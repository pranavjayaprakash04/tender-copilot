from __future__ import annotations

from datetime import datetime
from uuid import UUID

import structlog
from celery import Celery

from app.contexts.bid_generation.repository import (
    BidGenerationAnalyticsRepository,
    BidGenerationRepository,
    BidTemplateRepository,
)
from app.contexts.bid_generation.service import BidGenerationService
from app.contexts.tender_discovery.repository import TenderRepository
from app.database import get_async_session
from app.infrastructure.groq_client import GroqClient

logger = structlog.get_logger()

celery_app = Celery('bid_generation_tasks')
celery_app.config_from_object('app.celery_config')


@celery_app.task(
    bind=True,
    name="bid_generation.generate_bid",
    max_retries=3,
    default_retry_delay=60
)
def generate_bid_task(self, bid_id: str, company_id: str, tender_id: str, lang_code: str = "en") -> dict:
    """Generate bid content using AI (async processing)."""
    async def _generate_bid():
        async with get_async_session() as session:
            bid_service = BidGenerationService(
                bid_repo=BidGenerationRepository(session),
                template_repo=BidTemplateRepository(session),
                analytics_repo=BidGenerationAnalyticsRepository(session),
                tender_repo=TenderRepository(session),
                groq_client=GroqClient()
            )

            try:
                await bid_service.update_bid_status(UUID(bid_id), "processing")

                bid_generation = await bid_service.generate_bid_content_with_model(
                    UUID(bid_id), UUID(company_id), UUID(tender_id), lang_code, "PRIMARY"
                )

                await bid_service.update_bid_status(UUID(bid_id), "completed")
                await bid_service.record_bid_outcomes(UUID(bid_id))

                logger.info(
                    "bid_generation_task_completed",
                    bid_id=bid_id,
                    company_id=company_id,
                    tender_id=tender_id,
                )

                return {
                    "status": "completed",
                    "bid_id": bid_id,
                    "completed_at": datetime.utcnow().isoformat()
                }

            except Exception as exc:
                await bid_service.update_bid_status(UUID(bid_id), "failed")

                logger.error(
                    "bid_generation_task_failed",
                    bid_id=bid_id,
                    error=str(exc),
                    retry_count=self.request.retries
                )

                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=60, exc=exc)

                return {
                    "status": "failed",
                    "bid_id": bid_id,
                    "error": str(exc),
                    "failed_at": datetime.utcnow().isoformat()
                }

    import asyncio
    return asyncio.run(_generate_bid())


@celery_app.task(bind=True, name="bid_generation.cleanup_old_tasks", max_retries=2)
def cleanup_old_tasks_task(self) -> dict:
    """Clean up old bid generation tasks."""
    async def _cleanup():
        async with get_async_session() as session:
            bid_repo = BidGenerationRepository(session)
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            deleted_count = await bid_repo.delete_old_completed(cutoff_date)
            return {
                "status": "completed",
                "deleted_count": deleted_count,
            }

    import asyncio
    return asyncio.run(_cleanup())


celery_app.conf.beat_schedule = {
    'cleanup-old-tasks': {
        'task': 'bid_generation.cleanup_old_tasks',
        'schedule': 86400.0,
    },
}

celery_app.conf.timezone = 'UTC'
