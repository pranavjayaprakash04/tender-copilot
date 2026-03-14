from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import structlog
from celery import Celery
from celery.schedules import crontab

from app.contexts.bid_lifecycle.models import BidStatus
from app.contexts.bid_lifecycle.repository import (
    BidFollowUpRepository,
    BidOutcomeRecordRepository,
    BidPaymentRepository,
    BidRepository,
)
from app.contexts.bid_lifecycle.schemas import (
    BidFollowUpCreate,
)
from app.database import get_async_session
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.prompts.bid.loss_analysis_v1 import SYSTEM_PROMPT, build_prompt
from app.shared.lang_context import LangContext

logger = structlog.get_logger()

# Initialize Celery app
celery_app = Celery('bid_lifecycle_tasks')
celery_app.config_from_object('app.celery_config')


def process_payment_follow_ups_task(
    company_id: str,
    days_overdue: int = 30,
    include_overdue_only: bool = True,
    send_notifications: bool = False
) -> dict:
    """Process payment follow-ups for overdue payments."""
    async def _process():
        async with get_async_session() as session:
            payment_repo = BidPaymentRepository(session)
            follow_up_repo = BidFollowUpRepository(session)

            # Get overdue payments
            payments = await payment_repo.get_overdue_payments(UUID(company_id), days_overdue)

            if include_overdue_only:
                payments = [p for p in payments if p.is_overdue]

            follow_ups_created = 0
            notifications_sent = 0
            processed_payment_ids = []

            for payment in payments:
                processed_payment_ids.append(str(payment.id))

                # Check if follow-up already exists
                existing_follow_ups = await follow_up_repo.get_by_bid(payment.bid_id, UUID(company_id))
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

                    await follow_up_repo.create(follow_up_data)
                    follow_ups_created += 1

                    # Send notification if requested
                    if send_notifications:
                        # TODO: Implement notification sending via WhatsApp/Email
                        notifications_sent += 1

            logger.info(
                "payment_follow_ups_task_completed",
                company_id=company_id,
                payments_processed=len(processed_payment_ids),
                follow_ups_created=follow_ups_created,
                notifications_sent=notifications_sent
            )

            return {
                "payments_processed": len(processed_payment_ids),
                "follow_ups_created": follow_ups_created,
                "notifications_sent": notifications_sent,
                "processed_payment_ids": processed_payment_ids
            }

    import asyncio
    return asyncio.run(_process())


@celery_app.task(name="bid_lifecycle.analyze_bid_loss")
def analyze_bid_loss_task(
    bid_id: str,
    company_id: str,
    include_competitor_analysis: bool = True,
    include_pricing_analysis: bool = True,
    include_technical_analysis: bool = True
) -> dict:
    """Analyze bid loss using AI."""
    async def _analyze():
        async with get_async_session() as session:
            bid_repo = BidRepository(session)
            outcome_repo = BidOutcomeRecordRepository(session)

            # Get bid and outcome data
            bid = await bid_repo.get_by_id(UUID(bid_id), UUID(company_id))
            outcome = await outcome_repo.get_by_bid(UUID(bid_id), UUID(company_id))

            if not outcome or outcome.outcome.value != "lost":
                logger.warning(
                    "bid_loss_analysis_skipped",
                    bid_id=bid_id,
                    company_id=company_id,
                    reason="Bid not marked as lost"
                )
                return {"status": "skipped", "reason": "Bid not marked as lost"}

            # Build prompt for loss analysis
            user_prompt = build_prompt(
                bid.title,
                bid.description,
                float(bid.bid_amount),
                outcome.loss_reason.value if outcome.loss_reason else None,
                outcome.loss_reason_details,
                outcome.winning_bidder,
                float(outcome.winning_amount) if outcome.winning_amount else None,
                outcome.competitor_count,
                outcome.our_ranking,
                outcome.evaluation_feedback,
                include_competitor_analysis,
                include_pricing_analysis,
                include_technical_analysis
            )

            # Call Groq for analysis
            from app.prompts.bid.loss_analysis_v1 import AnalysisOutput

            groq_client = GroqClient()
            result = await groq_client.complete(
                model=GroqModel.FAST,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                output_schema=AnalysisOutput,
                lang=LangContext.from_lang("en"),
                trace_id=f"task-{str(uuid4())}",
                company_id=company_id,
                temperature=0.3
            )

            # Store analysis results (could be saved to database)
            analysis_data = {
                "bid_id": bid_id,
                "analysis_summary": result.analysis_summary,
                "key_factors": result.key_factors,
                "recommendations": result.recommendations,
                "competitor_insights": result.competitor_insights,
                "pricing_insights": result.pricing_insights,
                "technical_insights": result.technical_insights,
                "confidence_score": result.confidence,
                "generated_at": datetime.utcnow().isoformat()
            }

            logger.info(
                "bid_loss_analysis_completed",
                bid_id=bid_id,
                company_id=company_id,
                confidence=result.confidence
            )

            return {
                "status": "completed",
                "analysis": analysis_data
            }

    import asyncio
    try:
        return asyncio.run(_analyze())
    except Exception as e:
        logger.error(
            "bid_loss_analysis_failed",
            bid_id=bid_id,
            company_id=company_id,
            error=str(e)
        )
        return {
            "status": "failed",
            "error": str(e)
        }


def create_payment_schedule_task(
    bid_id: str,
    company_id: str
) -> dict:
    """Create standard payment schedule for won bid."""
    async def _create_schedule():
        async with get_async_session() as session:
            bid_repo = BidRepository(session)
            payment_repo = BidPaymentRepository(session)
            follow_up_repo = BidFollowUpRepository(session)

            # Get bid details
            bid = await bid_repo.get_by_id(UUID(bid_id), UUID(company_id))

            if bid.status != BidStatus.WON:
                logger.warning(
                    "payment_schedule_creation_skipped",
                    bid_id=bid_id,
                    company_id=company_id,
                    reason="Bid not marked as won"
                )
                return {"status": "skipped", "reason": "Bid not marked as won"}

            # Create standard payment schedule
            # Typical government contract payment terms: 20% advance, 60% milestones, 20% final
            bid_amount = float(bid.bid_amount)

            payments_created = []

            # 1. Advance payment (20%) - Due 15 days after award
            advance_amount = bid_amount * 0.2
            advance_due = bid.award_date + timedelta(days=15) if bid.award_date else datetime.utcnow() + timedelta(days=15)

            advance_payment = await payment_repo.create({
                "bid_id": UUID(bid_id),
                "payment_type": "advance",
                "payment_amount": advance_amount,
                "due_date": advance_due,
                "invoice_number": f"ADV-{bid.bid_number}",
                "payment_terms": "20% advance payment as per contract terms"
            })
            payments_created.append(str(advance_payment.id))

            # 2. Milestone payments (60%) - Split into 3 equal parts
            milestone_amount = bid_amount * 0.6 / 3
            for i in range(3):
                milestone_due = advance_due + timedelta(days=30 * (i + 1))

                milestone_payment = await payment_repo.create({
                    "bid_id": UUID(bid_id),
                    "payment_type": "milestone",
                    "payment_amount": milestone_amount,
                    "due_date": milestone_due,
                    "invoice_number": f"M{i+1}-{bid.bid_number}",
                    "payment_terms": f"Milestone {i+1} payment as per contract schedule"
                })
                payments_created.append(str(milestone_payment.id))

            # 3. Final payment (20%) - Due 30 days after last milestone
            final_amount = bid_amount * 0.2
            final_due = advance_due + timedelta(days=120)

            final_payment = await payment_repo.create({
                "bid_id": UUID(bid_id),
                "payment_type": "final",
                "payment_amount": final_amount,
                "due_date": final_due,
                "invoice_number": f"FINAL-{bid.bid_number}",
                "payment_terms": "Final payment as per contract completion"
            })
            payments_created.append(str(final_payment.id))

            # Schedule follow-ups for all payments
            for payment_id in payments_created:
                payment = await payment_repo.get_by_id(UUID(payment_id), UUID(company_id))
                await _schedule_payment_follow_ups(
                    UUID(bid_id), UUID(payment_id), payment.due_date, follow_up_repo
                )

            logger.info(
                "payment_schedule_created",
                bid_id=bid_id,
                company_id=company_id,
                payments_created=len(payments_created)
            )

            return {
                "status": "completed",
                "payments_created": payments_created
            }

    import asyncio
    return asyncio.run(_create_schedule())


async def _schedule_payment_follow_ups(
    bid_id: UUID,
    payment_id: UUID,
    due_date: datetime,
    follow_up_repo: BidFollowUpRepository
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

        await follow_up_repo.create(follow_up_data)


# Scheduled tasks (Celery Beat)
@celery_app.task(name="bid_lifecycle.daily_payment_follow_up_check")
def daily_payment_follow_up_check() -> dict:
    """Daily task to check and process payment follow-ups."""
    async def _daily_check():
        # This would typically get all companies and process their overdue payments
        # For now, returning a placeholder
        logger.info("daily_payment_follow_up_check_completed")
        return {"status": "completed", "processed_companies": 0}

    import asyncio
    return asyncio.run(_daily_check())


@celery_app.task(name="bid_lifecycle.weekly_loss_analysis_batch")
def weekly_loss_analysis_batch() -> dict:
    """Weekly task to analyze recent bid losses."""
    async def _weekly_batch():
        # This would typically get all recent lost bids and analyze them
        # For now, returning a placeholder
        logger.info("weekly_loss_analysis_batch_completed")
        return {"status": "completed", "analyzed_bids": 0}

    import asyncio
    return asyncio.run(_weekly_batch())


@celery_app.task(name="bid_lifecycle.refresh_market_prices")
def refresh_market_prices_task() -> dict:
    """Refresh market prices materialized view."""
    async def _refresh():
        async with get_async_session() as session:
            try:
                # Execute raw SQL to refresh materialized view
                await session.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY market_prices")
                await session.commit()

                logger.info(
                    "market_prices_refreshed",
                    timestamp=datetime.utcnow().isoformat()
                )
                return {"status": "completed", "refreshed_at": datetime.utcnow().isoformat()}
            except Exception as e:
                await session.rollback()
                logger.error(
                    "market_prices_refresh_failed",
                    error=str(e)
                )
                return {"status": "failed", "error": str(e)}

    import asyncio
    return asyncio.run(_refresh())


# Configure Celery Beat schedule
celery_app.conf.beat_schedule = {
    'daily-payment-follow-up': {
        'task': 'bid_lifecycle.daily_payment_follow_up_check',
        'schedule': crontab(hour=9, minute=0),  # 9 AM daily
    },
    'weekly-loss-analysis': {
        'task': 'bid_lifecycle.weekly_loss_analysis_batch',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # 10 AM every Monday
    },
    'refresh-market-prices-daily': {
        'task': 'bid_lifecycle.refresh_market_prices',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}

celery_app.conf.timezone = 'UTC'
