from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from celery import Celery

from app.contexts.tender_intelligence.clause_service import ClauseService
from app.contexts.tender_intelligence.repository import (
    DocumentChunkRepository,
    TenderDocumentRepository,
)
from app.database import get_async_session
from app.infrastructure.groq_client import GroqClient

logger = structlog.get_logger()

celery_app = Celery('tender_analysis_tasks')
celery_app.config_from_object('app.celery_config')


@celery_app.task(
    bind=True,
    name="tender_intelligence.extract_clauses",
    max_retries=3,
    default_retry_delay=300
)
def clause_extraction_task(
    self,
    tender_id: str,
    company_id: str,
    lang: str = "en"
) -> dict[str, Any]:
    """Extract clauses from tender document."""
    async def _extract_clauses():
        async with get_async_session() as session:
            # Initialize service
            clause_service = ClauseService(
                document_repo=TenderDocumentRepository(session),
                chunk_repo=DocumentChunkRepository(session),
                groq_client=GroqClient()
            )

            try:
                # Extract clauses
                result = await clause_service.extract_clauses(
                    UUID(tender_id), lang, UUID(company_id)
                )

                logger.info(
                    "clause_extraction_task_completed",
                    tender_id=tender_id,
                    company_id=company_id,
                    lang=lang,
                    clauses_count=len(result.clauses)
                )

                return {
                    "status": "completed",
                    "tender_id": tender_id,
                    "company_id": company_id,
                    "lang": lang,
                    "clauses_count": len(result.clauses),
                    "extracted_at": result.extracted_at.isoformat(),
                    "completed_at": datetime.utcnow().isoformat()
                }

            except Exception as exc:
                logger.error(
                    "clause_extraction_task_failed",
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
    return asyncio.run(_extract_clauses())


@celery_app.task(
    bind=True,
    name="tender_intelligence.detect_risks",
    max_retries=3,
    default_retry_delay=300
)
def risk_detection_task(
    self,
    tender_id: str,
    company_id: str,
    lang: str = "en"
) -> dict[str, Any]:
    """Detect risks in tender document."""
    async def _detect_risks():
        async with get_async_session() as session:
            # Initialize service
            clause_service = ClauseService(
                document_repo=TenderDocumentRepository(session),
                chunk_repo=DocumentChunkRepository(session),
                groq_client=GroqClient()
            )

            try:
                # Detect risks
                result = await clause_service.detect_risks(
                    UUID(tender_id), lang, UUID(company_id)
                )

                logger.info(
                    "risk_detection_task_completed",
                    tender_id=tender_id,
                    company_id=company_id,
                    lang=lang,
                    risk_level=result.risk_level,
                    risks_count=len(result.risks)
                )

                return {
                    "status": "completed",
                    "tender_id": tender_id,
                    "company_id": company_id,
                    "lang": lang,
                    "risk_level": result.risk_level,
                    "risks_count": len(result.risks),
                    "completed_at": datetime.utcnow().isoformat()
                }

            except Exception as exc:
                logger.error(
                    "risk_detection_task_failed",
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
    return asyncio.run(_detect_risks())


@celery_app.task(
    name="tender_intelligence.batch_analyze_tenders"
)
def batch_analyze_tenders_task() -> dict[str, Any]:
    """Batch analyze tenders for clauses and risks."""
    async def _batch_analyze():
        async with get_async_session() as session:
            document_repo = TenderDocumentRepository(session)

            try:
                # Get recent tenders without analysis
                from datetime import timedelta
                cutoff_date = datetime.utcnow() - timedelta(days=1)
                recent_tenders = await document_repo.get_recent_without_analysis(cutoff_date)

                processed_count = 0
                for tender in recent_tenders:
                    try:
                        # Trigger clause extraction
                        clause_extraction_task.delay(
                            str(tender.id), str(tender.company_id), "en"
                        )
                        # Trigger risk detection
                        risk_detection_task.delay(
                            str(tender.id), str(tender.company_id), "en"
                        )
                        processed_count += 1
                    except Exception as e:
                        logger.error(
                            "batch_analysis_trigger_failed",
                            tender_id=str(tender.id),
                            error=str(e)
                        )

                logger.info(
                    "batch_analysis_triggered",
                    tenders_count=len(recent_tenders),
                    processed_count=processed_count
                )

                return {
                    "status": "completed",
                    "tenders_found": len(recent_tenders),
                    "processed_count": processed_count,
                    "completed_at": datetime.utcnow().isoformat()
                }

            except Exception as exc:
                logger.error("batch_analysis_task_failed", error=str(exc))
                return {
                    "status": "failed",
                    "error": str(exc),
                    "failed_at": datetime.utcnow().isoformat()
                }

    import asyncio
    return asyncio.run(_batch_analyze())
