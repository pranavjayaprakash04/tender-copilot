from __future__ import annotations

from datetime import datetime
from typing import Any, dict
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
    default_retry_delay=60  # 1 minute retry for bid generation
)
def generate_bid_task(self, bid_id: str, company_id: str, tender_id: str, lang_code: str = "en") -> dict:
    """Generate bid content using AI (async processing)."""
    async def _generate_bid():
        async with get_async_session() as session:
            # Initialize service
            bid_service = BidGenerationService(
                bid_repo=BidGenerationRepository(session),
                template_repo=BidTemplateRepository(session),
                analytics_repo=BidGenerationAnalyticsRepository(session),
                tender_repo=TenderRepository(session),
                groq_client=GroqClient()
            )
            
            try:
                # Update bid status to processing
                await bid_service.update_bid_status(UUID(bid_id), "processing")
                
                # Generate bid content using GroqModel.PRIMARY
                bid_generation = await bid_service.generate_bid_content_with_model(
                    UUID(bid_id), UUID(company_id), UUID(tender_id), lang_code, "PRIMARY"
                )
                
                # Update bid status to completed
                await bid_service.update_bid_status(UUID(bid_id), "completed")
                
                # Trigger bid outcomes recording
                await bid_service.record_bid_outcomes(UUID(bid_id))
                
                logger.info(
                    "bid_generation_task_completed",
                    bid_id=bid_id,
                    company_id=company_id,
                    tender_id=tender_id,
                    lang_code=lang_code,
                    bid_type=bid_generation.bid_type,
                    processing_time_ms=bid_generation.processing_time_ms,
                    confidence_score=bid_generation.confidence_score
                )
                
                return {
                    "status": "completed",
                    "bid_id": bid_id,
                    "company_id": company_id,
                    "tender_id": tender_id,
                    "lang_code": lang_code,
                    "bid_generation_id": str(bid_generation.id),
                    "bid_type": bid_generation.bid_type,
                    "processing_time_ms": bid_generation.processing_time_ms,
                    "confidence_score": bid_generation.confidence_score,
                    "completed_at": datetime.utcnow().isoformat()
                }
                
            except Exception as exc:
                # Update bid status to failed
                await bid_service.update_bid_status(UUID(bid_id), "failed")
                
                logger.error(
                    "bid_generation_task_failed",
                    bid_id=bid_id,
                    company_id=company_id,
                    tender_id=tender_id,
                    lang_code=lang_code,
                    error=str(exc),
                    retry_count=self.request.retries
                )
                
                # Retry if we have attempts left
                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=60, exc=exc)
                
                return {
                    "status": "failed",
                    "bid_id": bid_id,
                    "company_id": company_id,
                    "tender_id": tender_id,
                    "lang_code": lang_code,
                    "error": str(exc),
                    "retry_count": self.request.retries,
                    "failed_at": datetime.utcnow().isoformat()
                }
    
    import asyncio
    return asyncio.run(_generate_bid())


@celery_app.task(
    bind=True,
    name="bid_generation.cleanup_old_tasks",
    max_retries=2,
    default_retry_delay=300
)
def cleanup_old_tasks_task(self) -> dict:
    """Clean up old bid generation tasks to maintain database performance."""
    async def _cleanup():
        async with get_async_session() as session:
            bid_repo = BidGenerationRepository(session)
            
            # Delete completed tasks older than 30 days
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            deleted_count = await bid_repo.delete_old_completed(cutoff_date)
            
            logger.info(
                "old_bid_tasks_cleaned",
                cutoff_date=cutoff_date.isoformat(),
                deleted_count=deleted_count
            )
            
            return {
                "status": "completed",
                "cutoff_date": cutoff_date.isoformat(),
                "deleted_count": deleted_count,
                "cleaned_at": datetime.utcnow().isoformat()
            }
    
    import asyncio
    return asyncio.run(_cleanup())


@celery_app.task(
    bind=True,
    name="bid_generation.update_analytics",
    max_retries=2,
    default_retry_delay=300
)
def update_analytics_task(self) -> dict:
    """Update bid generation analytics for all companies."""
    async def _update_analytics():
        async with get_async_session() as session:
            analytics_repo = BidGenerationAnalyticsRepository(session)
            
            try:
                # Update daily analytics for all companies
                updated_count = await analytics_repo.update_daily_analytics_for_all()
                
                logger.info(
                    "bid_analytics_updated",
                    companies_updated=updated_count,
                    updated_at=datetime.utcnow().isoformat()
                )
                
                return {
                    "status": "completed",
                    "companies_updated": updated_count,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
            except Exception as exc:
                logger.error(
                    "bid_analytics_update_failed",
                    error=str(exc),
                    retry_count=self.request.retries
                )
                
                # Retry if we have attempts left
                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=300, exc=exc)
                
                return {
                    "status": "failed",
                    "error": str(exc),
                    "retry_count": self.request.retries,
                    "failed_at": datetime.utcnow().isoformat()
                }
    
    import asyncio
    return asyncio.run(_update_analytics())


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-tasks': {
        'task': 'bid_generation.cleanup_old_tasks',
        'schedule': 86400.0,  # Daily at midnight
    },
    'update-analytics': {
        'task': 'bid_generation.update_analytics',
        'schedule': 3600.0,  # Every hour
    },
}

celery_app.conf.timezone = 'UTC'