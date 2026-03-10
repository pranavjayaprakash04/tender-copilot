from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.bid_lifecycle.models import (
    Bid,
    BidFollowUp,
    BidOutcomeRecord,
    BidPayment,
    BidStatus,
    PaymentStatus,
)
from app.contexts.bid_lifecycle.schemas import (
    BidCreate,
    BidFollowUpCreate,
    BidFollowUpUpdate,
    BidOutcomeRecordCreate,
    BidOutcomeRecordUpdate,
    BidPaymentCreate,
    BidPaymentUpdate,
    BidSearchFilters,
    BidUpdate,
)
from app.shared.exceptions import NotFoundException, ValidationException


class BidRepository:
    """Repository for Bid operations with state machine enforcement."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, bid_data: BidCreate) -> Bid:
        """Create a new bid."""
        # Check if bid number already exists for this company
        existing = await self._session.execute(
            select(Bid).where(
                and_(
                    Bid.company_id == bid_data.company_id,
                    Bid.bid_number == bid_data.bid_number
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationException("Bid number already exists for this company")

        bid = Bid(**bid_data.model_dump())
        self._session.add(bid)
        await self._session.commit()
        await self._session.refresh(bid)
        return bid

    async def get_by_id(self, bid_id: UUID, company_id: UUID) -> Bid:
        """Get bid by ID."""
        result = await self._session.execute(
            select(Bid).where(
                and_(Bid.id == bid_id, Bid.company_id == company_id)
            )
        )
        bid = result.scalar_one_or_none()
        if not bid:
            raise NotFoundException("Bid not found")
        return bid

    async def get_by_number(self, bid_number: str, company_id: UUID) -> Bid:
        """Get bid by number."""
        result = await self._session.execute(
            select(Bid).where(
                and_(Bid.bid_number == bid_number, Bid.company_id == company_id)
            )
        )
        bid = result.scalar_one_or_none()
        if not bid:
            raise NotFoundException("Bid not found")
        return bid

    async def get_by_company(
        self,
        company_id: UUID,
        filters: BidSearchFilters | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Bid], int]:
        """Get bids for a company with filters and pagination."""
        query = select(Bid).where(Bid.company_id == company_id)

        # Apply filters
        if filters:
            conditions = []

            if filters.search_query:
                conditions.append(
                    or_(
                        Bid.title.ilike(f"%{filters.search_query}%"),
                        Bid.description.ilike(f"%{filters.search_query}%"),
                        Bid.bid_number.ilike(f"%{filters.search_query}%"),
                        Bid.lead_bidder.ilike(f"%{filters.search_query}%")
                    )
                )

            if filters.status:
                conditions.append(Bid.status == filters.status)

            if filters.tender_id:
                conditions.append(Bid.tender_id == filters.tender_id)

            if filters.lead_bidder:
                conditions.append(Bid.lead_bidder == filters.lead_bidder)

            if filters.bid_manager:
                conditions.append(Bid.bid_manager == filters.bid_manager)

            if filters.min_amount:
                conditions.append(Bid.bid_amount >= filters.min_amount)

            if filters.max_amount:
                conditions.append(Bid.bid_amount <= filters.max_amount)

            if filters.submission_date_from:
                conditions.append(Bid.submission_date >= filters.submission_date_from)

            if filters.submission_date_to:
                conditions.append(Bid.submission_date <= filters.submission_date_to)

            if filters.deadline_from:
                conditions.append(Bid.submission_deadline >= filters.deadline_from)

            if filters.deadline_to:
                conditions.append(Bid.submission_deadline <= filters.deadline_to)

            if conditions:
                query = query.where(and_(*conditions))

        # Order by created date descending
        query = query.order_by(desc(Bid.created_at))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self._session.execute(query)
        bids = list(result.scalars().all())

        # Apply computed filters if specified
        if filters:
            if filters.is_editable is not None:
                bids = [bid for bid in bids if bid.can_edit == filters.is_editable]

            if filters.is_submittable is not None:
                bids = [bid for bid in bids if bid.can_submit == filters.is_submittable]

            if filters.has_overdue_payments is not None:
                bids = [bid for bid in bids if bid.is_overdue_payment == filters.has_overdue_payments]

        return bids, total

    async def update(self, bid_id: UUID, company_id: UUID, update_data: BidUpdate) -> Bid:
        """Update a bid."""
        bid = await self.get_by_id(bid_id, company_id)

        # Check if bid can be edited
        if not bid.can_edit:
            raise ValidationException(f"Bid cannot be edited in {bid.status} status")

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(bid, field, value)

        await self._session.commit()
        await self._session.refresh(bid)
        return bid

    async def delete(self, bid_id: UUID, company_id: UUID) -> None:
        """Delete a bid."""
        bid = await self.get_by_id(bid_id, company_id)

        # Check if bid can be deleted (only draft or cancelled)
        if bid.status not in [BidStatus.DRAFT, BidStatus.CANCELLED]:
            raise ValidationException(f"Bid cannot be deleted in {bid.status} status")

        await self._session.delete(bid)
        await self._session.commit()

    async def transition_status(
        self,
        bid_id: UUID,
        company_id: UUID,
        new_status: BidStatus,
        outcome_data: BidOutcomeRecordCreate | None = None,
        reason: str | None = None,
        internal_notes: str | None = None
    ) -> tuple[Bid, BidOutcomeRecord | None]:
        """Transition bid status with atomic outcome record enforcement."""
        bid = await self.get_by_id(bid_id, company_id)

        # Check if transition is allowed
        if not bid.can_transition_to(new_status):
            allowed_transitions = bid.get_allowed_transitions()
            raise ValidationException(
                f"Cannot transition from {bid.status} to {new_status}. "
                f"Allowed transitions: {allowed_transitions}"
            )

        # Check if outcome record is required for final statuses
        final_statuses = [BidStatus.WON, BidStatus.LOST, BidStatus.WITHDRAWN, BidStatus.DISQUALIFIED, BidStatus.CANCELLED]
        if new_status in final_statuses and not outcome_data:
            raise ValidationException(f"Outcome record is required for status {new_status}")

        # Begin atomic transaction
        previous_status = bid.status
        bid.previous_status = previous_status
        bid.status = new_status

        # Update relevant timestamps based on status
        now = datetime.utcnow()
        if new_status == BidStatus.SUBMITTED:
            bid.submission_date = now
        elif new_status == BidStatus.UNDER_EVALUATION:
            bid.evaluation_start_date = now
        elif new_status == BidStatus.AWARDED:
            bid.award_date = now

        # Add internal notes if provided
        if internal_notes:
            if bid.internal_notes:
                bid.internal_notes += f"\n\n[{now.strftime('%Y-%m-%d %H:%M')}] {internal_notes}"
            else:
                bid.internal_notes = f"[{now.strftime('%Y-%m-%d %H:%M')}] {internal_notes}"

        # Create outcome record if required
        outcome_record = None
        if outcome_data and new_status in final_statuses:
            outcome_data.bid_id = bid_id
            outcome_record = BidOutcomeRecord(**outcome_data.model_dump())
            self._session.add(outcome_record)

        await self._session.commit()
        await self._session.refresh(bid)

        if outcome_record:
            await self._session.refresh(outcome_record)

        return bid, outcome_record

    async def get_stats(self, company_id: UUID) -> dict:
        """Get bid statistics for a company."""
        # Total bids
        total_result = await self._session.execute(
            select(func.count(Bid.id)).where(Bid.company_id == company_id)
        )
        total = total_result.scalar()

        # Status-wise counts
        status_counts = {}
        for status in BidStatus:
            result = await self._session.execute(
                select(func.count(Bid.id)).where(
                    and_(Bid.company_id == company_id, Bid.status == status)
                )
            )
            status_counts[f"{status.value}_bids"] = result.scalar()

        # Financial statistics
        total_value_result = await self._session.execute(
            select(func.sum(Bid.bid_amount)).where(Bid.company_id == company_id)
        )
        total_value = total_value_result.scalar()

        won_value_result = await self._session.execute(
            select(func.sum(Bid.bid_amount)).where(
                and_(Bid.company_id == company_id, Bid.status == BidStatus.WON)
            )
        )
        won_value = won_value_result.scalar()

        # Win rate
        submitted_count = status_counts.get("submitted_bids", 0)
        won_count = status_counts.get("won_bids", 0)
        win_rate = (won_count / submitted_count * 100) if submitted_count > 0 else 0

        # Average bid amount
        avg_amount = (float(total_value) / total) if total > 0 else 0

        # This month statistics
        this_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        submissions_this_month_result = await self._session.execute(
            select(func.count(Bid.id)).where(
                and_(
                    Bid.company_id == company_id,
                    Bid.submission_date >= this_month_start
                )
            )
        )
        submissions_this_month = submissions_this_month_result.scalar()

        wins_this_month_result = await self._session.execute(
            select(func.count(Bid.id)).where(
                and_(
                    Bid.company_id == company_id,
                    Bid.status == BidStatus.WON,
                    Bid.award_date >= this_month_start
                )
            )
        )
        wins_this_month = wins_this_month_result.scalar()

        return {
            "total_bids": total,
            "draft_bids": status_counts.get("draft_bids", 0),
            "reviewing_bids": status_counts.get("reviewing_bids", 0),
            "submitted_bids": status_counts.get("submitted_bids", 0),
            "under_evaluation_bids": status_counts.get("under_evaluation_bids", 0),
            "awarded_bids": status_counts.get("awarded_bids", 0),
            "won_bids": status_counts.get("won_bids", 0),
            "lost_bids": status_counts.get("lost_bids", 0),
            "withdrawn_bids": status_counts.get("withdrawn_bids", 0),
            "disqualified_bids": status_counts.get("disqualified_bids", 0),
            "total_bid_value": float(total_value) if total_value else 0,
            "won_bid_value": float(won_value) if won_value else 0,
            "win_rate": win_rate,
            "average_bid_amount": avg_amount,
            "submissions_this_month": submissions_this_month,
            "wins_this_month": wins_this_month
        }

    async def bulk_update(self, bid_ids: list[UUID], company_id: UUID, update_data: BidUpdate) -> list[Bid]:
        """Bulk update bids."""
        # Verify all bids belong to the company and are editable
        result = await self._session.execute(
            select(Bid).where(
                and_(
                    Bid.id.in_(bid_ids),
                    Bid.company_id == company_id
                )
            )
        )
        bids = list(result.scalars().all())

        if len(bids) != len(bid_ids):
            raise ValidationException("Some bids not found or don't belong to this company")

        # Check if all bids can be edited
        non_editable = [bid for bid in bids if not bid.can_edit]
        if non_editable:
            raise ValidationException(f"Some bids cannot be edited: {[bid.id for bid in non_editable]}")

        update_dict = update_data.model_dump(exclude_unset=True)
        for bid in bids:
            for field, value in update_dict.items():
                setattr(bid, field, value)

        await self._session.commit()
        return bids

    async def bulk_status_transition(
        self,
        bid_ids: list[UUID],
        company_id: UUID,
        new_status: BidStatus,
        reason: str | None = None,
        internal_notes: str | None = None
    ) -> list[Bid]:
        """Bulk status transition (only for non-final statuses that don't require outcomes)."""
        # Check if new status requires outcome records
        final_statuses = [BidStatus.WON, BidStatus.LOST, BidStatus.WITHDRAWN, BidStatus.DISQUALIFIED, BidStatus.CANCELLED]
        if new_status in final_statuses:
            raise ValidationException(f"Bulk transition to {new_status} requires individual outcome records")

        # Verify all bids belong to the company
        result = await self._session.execute(
            select(Bid).where(
                and_(
                    Bid.id.in_(bid_ids),
                    Bid.company_id == company_id
                )
            )
        )
        bids = list(result.scalars().all())

        if len(bids) != len(bid_ids):
            raise ValidationException("Some bids not found or don't belong to this company")

        # Check if all bids can transition
        non_transitionable = []
        for bid in bids:
            if not bid.can_transition_to(new_status):
                non_transitionable.append(bid.id)

        if non_transitionable:
            raise ValidationException(f"Some bids cannot transition to {new_status}: {non_transitionable}")

        # Perform transitions
        now = datetime.utcnow()
        for bid in bids:
            bid.previous_status = bid.status
            bid.status = new_status

            if new_status == BidStatus.SUBMITTED:
                bid.submission_date = now
            elif new_status == BidStatus.UNDER_EVALUATION:
                bid.evaluation_start_date = now
            elif new_status == BidStatus.AWARDED:
                bid.award_date = now

        await self._session.commit()
        return bids


class BidOutcomeRecordRepository:
    """Repository for BidOutcomeRecord operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, outcome_data: BidOutcomeRecordCreate) -> BidOutcomeRecord:
        """Create a new bid outcome record."""
        outcome = BidOutcomeRecord(**outcome_data.model_dump())
        self._session.add(outcome)
        await self._session.commit()
        await self._session.refresh(outcome)
        return outcome

    async def get_by_id(self, outcome_id: UUID, company_id: UUID) -> BidOutcomeRecord:
        """Get outcome record by ID."""
        result = await self._session.execute(
            select(BidOutcomeRecord)
            .join(Bid, BidOutcomeRecord.bid_id == Bid.id)
            .where(
                and_(
                    BidOutcomeRecord.id == outcome_id,
                    Bid.company_id == company_id
                )
            )
        )
        outcome = result.scalar_one_or_none()
        if not outcome:
            raise NotFoundException("Outcome record not found")
        return outcome

    async def get_by_bid(self, bid_id: UUID, company_id: UUID) -> BidOutcomeRecord | None:
        """Get outcome record for a bid."""
        result = await self._session.execute(
            select(BidOutcomeRecord)
            .join(Bid, BidOutcomeRecord.bid_id == Bid.id)
            .where(
                and_(
                    BidOutcomeRecord.bid_id == bid_id,
                    Bid.company_id == company_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def update(self, outcome_id: UUID, company_id: UUID, update_data: BidOutcomeRecordUpdate) -> BidOutcomeRecord:
        """Update an outcome record."""
        outcome = await self.get_by_id(outcome_id, company_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(outcome, field, value)

        if update_data.verified and not outcome.verified:
            outcome.verified_at = datetime.utcnow()

        await self._session.commit()
        await self._session.refresh(outcome)
        return outcome

    async def delete(self, outcome_id: UUID, company_id: UUID) -> None:
        """Delete an outcome record."""
        outcome = await self.get_by_id(outcome_id, company_id)
        await self._session.delete(outcome)
        await self._session.commit()


class BidPaymentRepository:
    """Repository for BidPayment operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payment_data: BidPaymentCreate) -> BidPayment:
        """Create a new bid payment."""
        payment = BidPayment(**payment_data.model_dump())
        self._session.add(payment)
        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def get_by_id(self, payment_id: UUID, company_id: UUID) -> BidPayment:
        """Get payment by ID."""
        result = await self._session.execute(
            select(BidPayment)
            .join(Bid, BidPayment.bid_id == Bid.id)
            .where(
                and_(
                    BidPayment.id == payment_id,
                    Bid.company_id == company_id
                )
            )
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundException("Payment not found")
        return payment

    async def get_by_bid(self, bid_id: UUID, company_id: UUID) -> list[BidPayment]:
        """Get payments for a bid."""
        result = await self._session.execute(
            select(BidPayment)
            .join(Bid, BidPayment.bid_id == Bid.id)
            .where(
                and_(
                    BidPayment.bid_id == bid_id,
                    Bid.company_id == company_id
                )
            ).order_by(BidPayment.due_date)
        )
        return list(result.scalars().all())

    async def update(self, payment_id: UUID, company_id: UUID, update_data: BidPaymentUpdate) -> BidPayment:
        """Update a payment."""
        payment = await self.get_by_id(payment_id, company_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(payment, field, value)

        if update_data.paid_date and not payment.paid_amount:
            payment.paid_amount = payment.payment_amount

        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def delete(self, payment_id: UUID, company_id: UUID) -> None:
        """Delete a payment."""
        payment = await self.get_by_id(payment_id, company_id)
        await self._session.delete(payment)
        await self._session.commit()

    async def get_overdue_payments(self, company_id: UUID, days_overdue: int = 0) -> list[BidPayment]:
        """Get overdue payments."""
        overdue_threshold = datetime.utcnow() - timedelta(days=days_overdue)

        result = await self._session.execute(
            select(BidPayment)
            .join(Bid, BidPayment.bid_id == Bid.id)
            .where(
                and_(
                    Bid.company_id == company_id,
                    BidPayment.due_date <= overdue_threshold,
                    BidPayment.status != PaymentStatus.FULLY_PAID,
                    BidPayment.status != PaymentStatus.DISPUTED
                )
            ).order_by(BidPayment.due_date)
        )
        return list(result.scalars().all())


class BidFollowUpRepository:
    """Repository for BidFollowUp operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, follow_up_data: BidFollowUpCreate) -> BidFollowUp:
        """Create a new follow-up."""
        follow_up = BidFollowUp(**follow_up_data.model_dump())
        self._session.add(follow_up)
        await self._session.commit()
        await self._session.refresh(follow_up)
        return follow_up

    async def get_by_id(self, follow_up_id: UUID, company_id: UUID) -> BidFollowUp:
        """Get follow-up by ID."""
        result = await self._session.execute(
            select(BidFollowUp)
            .join(Bid, BidFollowUp.bid_id == Bid.id)
            .where(
                and_(
                    BidFollowUp.id == follow_up_id,
                    Bid.company_id == company_id
                )
            )
        )
        follow_up = result.scalar_one_or_none()
        if not follow_up:
            raise NotFoundException("Follow-up not found")
        return follow_up

    async def get_by_bid(self, bid_id: UUID, company_id: UUID) -> list[BidFollowUp]:
        """Get follow-ups for a bid."""
        result = await self._session.execute(
            select(BidFollowUp)
            .join(Bid, BidFollowUp.bid_id == Bid.id)
            .where(
                and_(
                    BidFollowUp.bid_id == bid_id,
                    Bid.company_id == company_id
                )
            ).order_by(BidFollowUp.scheduled_date)
        )
        return list(result.scalars().all())

    async def get_overdue(self, company_id: UUID) -> list[BidFollowUp]:
        """Get overdue follow-ups."""
        result = await self._session.execute(
            select(BidFollowUp)
            .join(Bid, BidFollowUp.bid_id == Bid.id)
            .where(
                and_(
                    Bid.company_id == company_id,
                    BidFollowUp.scheduled_date <= datetime.utcnow(),
                    BidFollowUp.status != "completed"
                )
            ).order_by(BidFollowUp.scheduled_date)
        )
        return list(result.scalars().all())

    async def update(self, follow_up_id: UUID, company_id: UUID, update_data: BidFollowUpUpdate) -> BidFollowUp:
        """Update a follow-up."""
        follow_up = await self.get_by_id(follow_up_id, company_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(follow_up, field, value)

        if update_data.status == "completed" and not follow_up.completed_date:
            follow_up.completed_date = datetime.utcnow()

        await self._session.commit()
        await self._session.refresh(follow_up)
        return follow_up

    async def delete(self, follow_up_id: UUID, company_id: UUID) -> None:
        """Delete a follow-up."""
        follow_up = await self.get_by_id(follow_up_id, company_id)
        await self._session.delete(follow_up)
        await self._session.commit()
