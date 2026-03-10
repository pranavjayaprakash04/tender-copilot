from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import structlog

from app.contexts.bid_lifecycle.models import (
    BidOutcome,
    BidStatus,
    PaymentStatus,
)
from app.contexts.bid_lifecycle.repository import (
    BidFollowUpRepository,
    BidOutcomeRecordRepository,
    BidPaymentRepository,
    BidRepository,
)
from app.contexts.bid_lifecycle.schemas import (
    BidBulkStatusTransition,
    BidBulkUpdate,
    BidCreate,
    BidFollowUpCreate,
    BidFollowUpResponse,
    BidFollowUpUpdate,
    BidListResponse,
    BidOutcomeRecordCreate,
    BidOutcomeRecordResponse,
    BidOutcomeRecordUpdate,
    BidPaymentCreate,
    BidPaymentResponse,
    BidPaymentUpdate,
    BidResponse,
    BidSearchFilters,
    BidStatsResponse,
    BidStatusTransition,
    BidUpdate,
    LossAnalysisRequest,
    LossAnalysisResponse,
    PaymentFollowUpRequest,
    PaymentFollowUpResponse,
)
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.prompts.bid.loss_analysis_v1 import SYSTEM_PROMPT, build_prompt
from app.shared.exceptions import ValidationException
from app.shared.lang_context import LangContext

logger = structlog.get_logger()


class BidLifecycleService:
    """Service for bid lifecycle operations with state machine and analysis."""

    def __init__(
        self,
        bid_repo: BidRepository,
        outcome_repo: BidOutcomeRecordRepository,
        payment_repo: BidPaymentRepository,
        follow_up_repo: BidFollowUpRepository,
        groq_client: GroqClient,
    ) -> None:
        self._bid_repo = bid_repo
        self._outcome_repo = outcome_repo
        self._payment_repo = payment_repo
        self._follow_up_repo = follow_up_repo
        self._groq = groq_client

    async def create_bid(
        self,
        bid_data: BidCreate,
        trace_id: str | None = None
    ) -> BidResponse:
        """Create a new bid."""
        try:
            bid = await self._bid_repo.create(bid_data)

            logger.info(
                "bid_created",
                trace_id=trace_id,
                bid_id=bid.id,
                company_id=bid.company_id,
                bid_number=bid.bid_number,
                tender_id=bid.tender_id
            )

            return BidResponse.model_validate(bid)

        except Exception as e:
            logger.error(
                "bid_creation_failed",
                trace_id=trace_id,
                company_id=bid_data.company_id,
                bid_number=bid_data.bid_number,
                error=str(e)
            )
            raise ValidationException(f"Failed to create bid: {e}")

    async def get_bid(
        self,
        bid_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidResponse:
        """Get a bid by ID."""
        bid = await self._bid_repo.get_by_id(bid_id, company_id)

        logger.info(
            "bid_retrieved",
            trace_id=trace_id,
            bid_id=bid_id,
            company_id=company_id
        )

        return BidResponse.model_validate(bid)

    async def list_bids(
        self,
        company_id: UUID,
        filters: BidSearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
        trace_id: str | None = None
    ) -> BidListResponse:
        """List bids for a company with filters."""
        bids, total = await self._bid_repo.get_by_company(
            company_id, filters, page, page_size
        )

        logger.info(
            "bids_listed",
            trace_id=trace_id,
            company_id=company_id,
            total=total,
            page=page,
            page_size=page_size
        )

        return BidListResponse(
            bids=[BidResponse.model_validate(bid) for bid in bids],
            total=total,
            page=page,
            page_size=page_size,
            has_next=page * page_size < total,
            has_previous=page > 1
        )

    async def update_bid(
        self,
        bid_id: UUID,
        company_id: UUID,
        update_data: BidUpdate,
        trace_id: str | None = None
    ) -> BidResponse:
        """Update a bid."""
        bid = await self._bid_repo.update(bid_id, company_id, update_data)

        logger.info(
            "bid_updated",
            trace_id=trace_id,
            bid_id=bid_id,
            company_id=company_id,
            updates=update_data.model_dump(exclude_unset=True)
        )

        return BidResponse.model_validate(bid)

    async def delete_bid(
        self,
        bid_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Delete a bid."""
        await self._bid_repo.delete(bid_id, company_id)

        logger.info(
            "bid_deleted",
            trace_id=trace_id,
            bid_id=bid_id,
            company_id=company_id
        )

    async def transition_bid_status(
        self,
        bid_id: UUID,
        company_id: UUID,
        status_transition: BidStatusTransition,
        outcome_data: BidOutcomeRecordCreate | None = None,
        trace_id: str | None = None
    ) -> tuple[BidResponse, BidOutcomeRecordResponse | None]:
        """Transition bid status with atomic outcome record enforcement."""
        bid, outcome_record = await self._bid_repo.transition_status(
            bid_id, company_id, status_transition.new_status,
            outcome_data, status_transition.reason, status_transition.internal_notes
        )

        # Trigger loss analysis if bid was lost
        if status_transition.new_status == BidStatus.LOST and outcome_record:
            await self._trigger_loss_analysis(bid_id, company_id, trace_id)

        # Create payment follow-ups for won bids
        if status_transition.new_status == BidStatus.WON:
            await self._create_payment_schedule(bid_id, company_id, trace_id)

        logger.info(
            "bid_status_transitioned",
            trace_id=trace_id,
            bid_id=bid_id,
            company_id=company_id,
            old_status=bid.previous_status,
            new_status=bid.status,
            outcome_created=bool(outcome_record)
        )

        bid_response = BidResponse.model_validate(bid)
        outcome_response = BidOutcomeRecordResponse.model_validate(outcome_record) if outcome_record else None

        return bid_response, outcome_response

    async def get_bid_stats(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidStatsResponse:
        """Get bid statistics for a company."""
        stats = await self._bid_repo.get_stats(company_id)

        logger.info(
            "bid_stats_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            total_bids=stats["total_bids"]
        )

        return BidStatsResponse(**stats)

    async def bulk_update_bids(
        self,
        bulk_data: BidBulkUpdate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[BidResponse]:
        """Bulk update bids."""
        bids = await self._bid_repo.bulk_update(
            bulk_data.bid_ids, company_id, bulk_data.updates
        )

        logger.info(
            "bids_bulk_updated",
            trace_id=trace_id,
            company_id=company_id,
            bid_count=len(bids)
        )

        return [BidResponse.model_validate(bid) for bid in bids]

    async def bulk_transition_bids(
        self,
        bulk_data: BidBulkStatusTransition,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[BidResponse]:
        """Bulk transition bid statuses."""
        bids = await self._bid_repo.bulk_status_transition(
            bulk_data.bid_ids, company_id, bulk_data.new_status,
            bulk_data.reason, bulk_data.internal_notes
        )

        logger.info(
            "bids_bulk_transitioned",
            trace_id=trace_id,
            company_id=company_id,
            bid_count=len(bids),
            new_status=bulk_data.new_status
        )

        return [BidResponse.model_validate(bid) for bid in bids]

    # Outcome Management
    async def create_outcome_record(
        self,
        outcome_data: BidOutcomeRecordCreate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidOutcomeRecordResponse:
        """Create a bid outcome record."""
        outcome = await self._outcome_repo.create(outcome_data)

        logger.info(
            "outcome_record_created",
            trace_id=trace_id,
            outcome_id=outcome.id,
            bid_id=outcome.bid_id,
            outcome=outcome.outcome
        )

        return BidOutcomeRecordResponse.model_validate(outcome)

    async def get_outcome_record(
        self,
        outcome_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidOutcomeRecordResponse:
        """Get outcome record by ID."""
        outcome = await self._outcome_repo.get_by_id(outcome_id, company_id)

        logger.info(
            "outcome_record_retrieved",
            trace_id=trace_id,
            outcome_id=outcome_id,
            company_id=company_id
        )

        return BidOutcomeRecordResponse.model_validate(outcome)

    async def update_outcome_record(
        self,
        outcome_id: UUID,
        company_id: UUID,
        update_data: BidOutcomeRecordUpdate,
        trace_id: str | None = None
    ) -> BidOutcomeRecordResponse:
        """Update an outcome record."""
        outcome = await self._outcome_repo.update(outcome_id, company_id, update_data)

        logger.info(
            "outcome_record_updated",
            trace_id=trace_id,
            outcome_id=outcome_id,
            company_id=company_id
        )

        return BidOutcomeRecordResponse.model_validate(outcome)

    async def delete_outcome_record(
        self,
        outcome_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Delete an outcome record."""
        await self._outcome_repo.delete(outcome_id, company_id)

        logger.info(
            "outcome_record_deleted",
            trace_id=trace_id,
            outcome_id=outcome_id,
            company_id=company_id
        )

    # Payment Management
    async def create_payment(
        self,
        payment_data: BidPaymentCreate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidPaymentResponse:
        """Create a bid payment."""
        payment = await self._payment_repo.create(payment_data)

        # Schedule follow-up if payment is not fully paid
        if payment.status != PaymentStatus.FULLY_PAID:
            await self._schedule_payment_follow_up(
                payment_data.bid_id, payment.id, payment.due_date, trace_id
            )

        logger.info(
            "payment_created",
            trace_id=trace_id,
            payment_id=payment.id,
            bid_id=payment.bid_id,
            amount=payment.payment_amount
        )

        return BidPaymentResponse.model_validate(payment)

    async def get_payment(
        self,
        payment_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidPaymentResponse:
        """Get payment by ID."""
        payment = await self._payment_repo.get_by_id(payment_id, company_id)

        logger.info(
            "payment_retrieved",
            trace_id=trace_id,
            payment_id=payment_id,
            company_id=company_id
        )

        return BidPaymentResponse.model_validate(payment)

    async def get_bid_payments(
        self,
        bid_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[BidPaymentResponse]:
        """Get payments for a bid."""
        payments = await self._payment_repo.get_by_bid(bid_id, company_id)

        logger.info(
            "bid_payments_retrieved",
            trace_id=trace_id,
            bid_id=bid_id,
            company_id=company_id,
            count=len(payments)
        )

        return [BidPaymentResponse.model_validate(payment) for payment in payments]

    async def update_payment(
        self,
        payment_id: UUID,
        company_id: UUID,
        update_data: BidPaymentUpdate,
        trace_id: str | None = None
    ) -> BidPaymentResponse:
        """Update a payment."""
        payment = await self._payment_repo.update(payment_id, company_id, update_data)

        logger.info(
            "payment_updated",
            trace_id=trace_id,
            payment_id=payment_id,
            company_id=company_id
        )

        return BidPaymentResponse.model_validate(payment)

    async def delete_payment(
        self,
        payment_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Delete a payment."""
        await self._payment_repo.delete(payment_id, company_id)

        logger.info(
            "payment_deleted",
            trace_id=trace_id,
            payment_id=payment_id,
            company_id=company_id
        )

    async def get_overdue_payments(
        self,
        company_id: UUID,
        days_overdue: int = 0,
        trace_id: str | None = None
    ) -> list[BidPaymentResponse]:
        """Get overdue payments."""
        payments = await self._payment_repo.get_overdue_payments(company_id, days_overdue)

        logger.info(
            "overdue_payments_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            days_overdue=days_overdue,
            count=len(payments)
        )

        return [BidPaymentResponse.model_validate(payment) for payment in payments]

    async def process_payment_follow_ups(
        self,
        request: PaymentFollowUpRequest,
        company_id: UUID,
        trace_id: str | None = None
    ) -> PaymentFollowUpResponse:
        """Process payment follow-ups for overdue payments."""
        # Get overdue payments
        payments = await self._payment_repo.get_overdue_payments(company_id, request.days_overdue)

        if request.include_overdue_only:
            payments = [p for p in payments if p.is_overdue]

        follow_ups_created = 0
        notifications_sent = 0
        processed_payment_ids = []

        for payment in payments:
            processed_payment_ids.append(payment.id)

            # Check if follow-up already exists
            existing_follow_ups = await self._follow_up_repo.get_by_bid(payment.bid_id, company_id)
            follow_up_exists = any(
                fu.payment_id == payment.id and fu.status == "pending"
                for fu in existing_follow_ups
            )

            if not follow_up_exists:
                # Create follow-up
                follow_up_data = BidFollowUpCreate(
                    bid_id=payment.bid_id,
                    payment_id=payment.id,
                    follow_up_type="payment",
                    priority="high" if payment.days_overdue > 30 else "medium",
                    contact_method="email",
                    scheduled_date=datetime.utcnow() + timedelta(days=1),
                    subject=f"Overdue Payment Follow-up - {payment.invoice_number or 'Payment'}",
                    message=f"Payment of ₹{payment.payment_amount:,.2f} is {payment.days_overdue} days overdue. Due date was {payment.due_date.strftime('%Y-%m-%d')}."
                )

                await self._follow_up_repo.create(follow_up_data)
                follow_ups_created += 1

                # Send notification if requested
                if request.send_notifications:
                    # TODO: Implement notification sending
                    notifications_sent += 1

        logger.info(
            "payment_follow_ups_processed",
            trace_id=trace_id,
            company_id=company_id,
            payments_processed=len(processed_payment_ids),
            follow_ups_created=follow_ups_created,
            notifications_sent=notifications_sent
        )

        return PaymentFollowUpResponse(
            payments_processed=len(processed_payment_ids),
            follow_ups_created=follow_ups_created,
            notifications_sent=notifications_sent,
            processed_payment_ids=processed_payment_ids
        )

    # Follow-up Management
    async def create_follow_up(
        self,
        follow_up_data: BidFollowUpCreate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidFollowUpResponse:
        """Create a follow-up."""
        follow_up = await self._follow_up_repo.create(follow_up_data)

        logger.info(
            "follow_up_created",
            trace_id=trace_id,
            follow_up_id=follow_up.id,
            bid_id=follow_up.bid_id,
            type=follow_up.follow_up_type
        )

        return BidFollowUpResponse.model_validate(follow_up)

    async def get_follow_up(
        self,
        follow_up_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> BidFollowUpResponse:
        """Get follow-up by ID."""
        follow_up = await self._follow_up_repo.get_by_id(follow_up_id, company_id)

        logger.info(
            "follow_up_retrieved",
            trace_id=trace_id,
            follow_up_id=follow_up_id,
            company_id=company_id
        )

        return BidFollowUpResponse.model_validate(follow_up)

    async def get_bid_follow_ups(
        self,
        bid_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[BidFollowUpResponse]:
        """Get follow-ups for a bid."""
        follow_ups = await self._follow_up_repo.get_by_bid(bid_id, company_id)

        logger.info(
            "bid_follow_ups_retrieved",
            trace_id=trace_id,
            bid_id=bid_id,
            company_id=company_id,
            count=len(follow_ups)
        )

        return [BidFollowUpResponse.model_validate(follow_up) for follow_up in follow_ups]

    async def update_follow_up(
        self,
        follow_up_id: UUID,
        company_id: UUID,
        update_data: BidFollowUpUpdate,
        trace_id: str | None = None
    ) -> BidFollowUpResponse:
        """Update a follow-up."""
        follow_up = await self._follow_up_repo.update(follow_up_id, company_id, update_data)

        logger.info(
            "follow_up_updated",
            trace_id=trace_id,
            follow_up_id=follow_up_id,
            company_id=company_id
        )

        return BidFollowUpResponse.model_validate(follow_up)

    async def delete_follow_up(
        self,
        follow_up_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Delete a follow-up."""
        await self._follow_up_repo.delete(follow_up_id, company_id)

        logger.info(
            "follow_up_deleted",
            trace_id=trace_id,
            follow_up_id=follow_up_id,
            company_id=company_id
        )

    async def get_overdue_follow_ups(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[BidFollowUpResponse]:
        """Get overdue follow-ups."""
        follow_ups = await self._follow_up_repo.get_overdue(company_id)

        logger.info(
            "overdue_follow_ups_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            count=len(follow_ups)
        )

        return [BidFollowUpResponse.model_validate(follow_up) for follow_up in follow_ups]

    # Analysis
    async def analyze_loss(
        self,
        request: LossAnalysisRequest,
        lang: LangContext = LangContext.from_lang("en"),
        trace_id: str | None = None,
        company_id: str | None = None
    ) -> LossAnalysisResponse:
        """Analyze bid loss using AI."""
        try:
            # Get bid and outcome data
            bid = await self._bid_repo.get_by_id(request.bid_id, UUID(company_id))
            outcome = await self._outcome_repo.get_by_bid(request.bid_id, UUID(company_id))

            if not outcome or outcome.outcome != BidOutcome.LOST:
                raise ValidationException("Bid is not marked as lost")

            # Build prompt for loss analysis
            user_prompt = build_prompt(
                bid.title,
                bid.description,
                bid.bid_amount,
                outcome.loss_reason,
                outcome.loss_reason_details,
                outcome.winning_bidder,
                outcome.winning_amount,
                outcome.competitor_count,
                outcome.our_ranking,
                outcome.evaluation_feedback,
                request.include_competitor_analysis,
                request.include_pricing_analysis,
                request.include_technical_analysis
            )

            # Call Groq for analysis
            from app.prompts.bid.loss_analysis_v1 import AnalysisOutput

            result = await self._groq.complete(
                model=GroqModel.FAST,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                output_schema=AnalysisOutput,
                lang=lang,
                trace_id=trace_id,
                company_id=company_id,
                temperature=0.3
            )

            logger.info(
                "loss_analysis_completed",
                trace_id=trace_id,
                bid_id=request.bid_id,
                confidence=result.confidence
            )

            return LossAnalysisResponse(
                bid_id=request.bid_id,
                analysis_summary=result.analysis_summary,
                key_factors=result.key_factors,
                recommendations=result.recommendations,
                competitor_insights=result.competitor_insights,
                pricing_insights=result.pricing_insights,
                technical_insights=result.technical_insights,
                confidence_score=result.confidence,
                generated_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(
                "loss_analysis_failed",
                trace_id=trace_id,
                bid_id=request.bid_id,
                error=str(e)
            )
            raise ValidationException(f"Failed to analyze loss: {e}")

    # Private helper methods
    async def _trigger_loss_analysis(
        self,
        bid_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Trigger loss analysis task."""
        # TODO: Queue Celery task for loss analysis
        logger.info(
            "loss_analysis_triggered",
            trace_id=trace_id,
            bid_id=bid_id,
            company_id=company_id
        )

    async def _create_payment_schedule(
        self,
        bid_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Create standard payment schedule for won bid."""
        # TODO: Create standard payment schedule (advance, milestones, final)
        logger.info(
            "payment_schedule_created",
            trace_id=trace_id,
            bid_id=bid_id,
            company_id=company_id
        )

    async def _schedule_payment_follow_up(
        self,
        bid_id: UUID,
        payment_id: UUID,
        due_date: datetime,
        trace_id: str | None = None
    ) -> None:
        """Schedule payment follow-up reminders."""
        # Schedule follow-ups at 30, 60, 90 days overdue
        follow_up_intervals = [30, 60, 90]

        for days in follow_up_intervals:
            follow_up_date = due_date + timedelta(days=days)

            follow_up_data = BidFollowUpCreate(
                bid_id=bid_id,
                payment_id=payment_id,
                follow_up_type="payment",
                priority="medium",
                contact_method="email",
                scheduled_date=follow_up_date,
                subject=f"Payment Follow-up - Day {days} Overdue",
                message=f"Payment is {days} days overdue. Please follow up with the client."
            )

            await self._follow_up_repo.create(follow_up_data)

        logger.info(
            "payment_follow_ups_scheduled",
            trace_id=trace_id,
            bid_id=bid_id,
            payment_id=payment_id,
            intervals=follow_up_intervals
        )
