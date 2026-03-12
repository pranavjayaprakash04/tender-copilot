from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from celery import Celery
from celery.schedules import crontab

from app.contexts.tender_intelligence.repository import (
    DocumentChunkRepository,
    TenderDocumentRepository,
)
from app.contexts.tender_intelligence.service import TenderIntelligenceService
from app.database import get_async_session
from app.infrastructure.groq_client import GroqClient

logger = structlog.get_logger()


celery_app = Celery('tender_intelligence_tasks')
celery_app.config_from_object('app.celery_config')


@celery_app.task(
    bind=True,
    name="tender_intelligence.explain_tender",
    max_retries=3,
    default_retry_delay=300
)
def explain_tender_task(
    self,
    tender_id: str,
    company_id: str,
    lang: str = "en"
) -> dict[str, Any]:
    """Explain tender in natural language."""
    async def _explain():
        async with get_async_session() as session:
            # Initialize service
            intelligence_service = TenderIntelligenceService(
                document_repo=TenderDocumentRepository(session),
                chunk_repo=DocumentChunkRepository(session),
                groq_client=GroqClient()
            )

            try:
                # Explain tender
                result = await intelligence_service.explain_tender(
                    UUID(tender_id), lang, UUID(company_id)
                )

                logger.info(
                    "tender_explanation_task_completed",
                    tender_id=tender_id,
                    company_id=company_id,
                    lang=lang,
                    summary_length=len(result.summary)
                )

                return {
                    "status": "completed",
                    "tender_id": tender_id,
                    "company_id": company_id,
                    "lang": lang,
                    "summary_length": len(result.summary),
                    "requirements_count": len(result.key_requirements),
                    "eligibility_count": len(result.eligibility),
                    "red_flags_count": len(result.red_flags),
                    "completed_at": datetime.utcnow().isoformat()
                }

            except Exception as exc:
                logger.error(
                    "tender_explanation_task_failed",
                    tender_id=tender_id,
                    company_id=company_id,
                    lang=lang,
                    error=str(exc),
                    retry_count=self.request.retries
                )

                # Retry if we have attempts left
                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=300, exc=exc)

                return {
                    "status": "failed",
                    "tender_id": tender_id,
                    "company_id": company_id,
                    "lang": lang,
                    "error": str(exc),
                    "retry_count": self.request.retries,
                    "failed_at": datetime.utcnow().isoformat()
                }

    import asyncio
    return asyncio.run(_explain())


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'batch-analyze-tenders': {
        'task': 'tender_intelligence.batch_analyze_tenders',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily - batch analyze tenders
    },
}

celery_app.conf.timezone = 'UTC'
