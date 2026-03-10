from __future__ import annotations

from datetime import datetime
from typing import dict
from uuid import UUID

import structlog
from celery import Celery
from celery.schedules import crontab

from app.contexts.tender_intelligence.repository import (
    DocumentChunkRepository,
    TenderDocumentRepository,
    TenderIntelligenceReportRepository,
)
from app.contexts.tender_intelligence.service import TenderIntelligenceService
from app.database import get_async_session
from app.infrastructure.groq_client import GroqClient

logger = structlog.get_logger()

celery_app = Celery('tender_intelligence_tasks')
celery_app.config_from_object('app.celery_config')


@celery_app.task(
    bind=True,
    name="tender_intelligence.process_document",
    max_retries=3,
    default_retry_delay=300  # 5 minutes retry for AI processing timeouts
)
def process_document_task(self, document_id: str, company_id: str) -> dict:
    """Process a tender document with PDF parsing and AI analysis."""
    async def _process():
        async with get_async_session() as session:
            # Initialize service
            intelligence_service = TenderIntelligenceService(
                document_repo=TenderDocumentRepository(session),
                chunk_repo=DocumentChunkRepository(session),
                report_repo=TenderIntelligenceReportRepository(session),
                groq_client=GroqClient()
            )

            try:
                # Process the document
                document = await intelligence_service.process_document(
                    UUID(document_id), UUID(company_id), f"task-{document_id}"
                )

                logger.info(
                    "document_processing_task_completed",
                    document_id=document_id,
                    company_id=company_id,
                    processing_status=document.processing_status.value,
                    confidence_score=document.ai_confidence_score
                )

                return {
                    "status": "completed",
                    "document_id": document_id,
                    "company_id": company_id,
                    "processing_status": document.processing_status.value,
                    "text_length": document.text_length,
                    "chunks_count": len(document.chunks) if hasattr(document, 'chunks') else 0,
                    "confidence_score": document.ai_confidence_score,
                    "processed_at": datetime.utcnow().isoformat()
                }

            except Exception as exc:
                logger.error(
                    "document_processing_task_failed",
                    document_id=document_id,
                    company_id=company_id,
                    error=str(exc),
                    retry_count=self.request.retries
                )

                # Retry if we have attempts left
                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=300, exc=exc)

                return {
                    "status": "failed",
                    "document_id": document_id,
                    "company_id": company_id,
                    "error": str(exc),
                    "retry_count": self.request.retries,
                    "failed_at": datetime.utcnow().isoformat()
                }

    import asyncio
    return asyncio.run(_process())


@celery_app.task(
    bind=True,
    name="tender_intelligence.generate_intelligence_report",
    max_retries=3,
    default_retry_delay=300
)
def generate_intelligence_report_task(
    self,
    tender_id: str,
    company_id: str,
    report_type: str = "summary",
    language: str = "en"
) -> dict:
    """Generate comprehensive intelligence report for a tender."""
    async def _generate_report():
        async with get_async_session() as session:
            # Initialize service
            intelligence_service = TenderIntelligenceService(
                document_repo=TenderDocumentRepository(session),
                chunk_repo=DocumentChunkRepository(session),
                report_repo=TenderIntelligenceReportRepository(session),
                groq_client=GroqClient()
            )

            try:
                # Generate intelligence report
                report = await intelligence_service.generate_intelligence_report(
                    UUID(tender_id), UUID(company_id), report_type, language, f"task-{tender_id}"
                )

                logger.info(
                    "intelligence_report_task_completed",
                    tender_id=tender_id,
                    company_id=company_id,
                    report_type=report_type,
                    language=language,
                    confidence_score=report.confidence_score,
                    documents_analyzed=report.total_documents_analyzed
                )

                return {
                    "status": "completed",
                    "tender_id": tender_id,
                    "company_id": company_id,
                    "report_id": str(report.id),
                    "report_type": report_type,
                    "language": language,
                    "confidence_score": report.confidence_score,
                    "documents_analyzed": report.total_documents_analyzed,
                    "pages_processed": report.total_pages_processed,
                    "processing_time_ms": report.processing_time_ms,
                    "generated_at": datetime.utcnow().isoformat()
                }

            except Exception as exc:
                logger.error(
                    "intelligence_report_task_failed",
                    tender_id=tender_id,
                    company_id=company_id,
                    report_type=report_type,
                    language=language,
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
                    "report_type": report_type,
                    "language": language,
                    "error": str(exc),
                    "retry_count": self.request.retries,
                    "failed_at": datetime.utcnow().isoformat()
                }

    import asyncio
    return asyncio.run(_generate_report())


@celery_app.task(
    bind=True,
    name="tender_intelligence.batch_process_documents",
    max_retries=2,
    default_retry_delay=600  # 10 minutes for batch processing
)
def batch_process_documents_task(self, company_id: str) -> dict:
    """Batch process all pending documents for a company."""
    async def _batch_process():
        async with get_async_session() as session:
            # Initialize service
            intelligence_service = TenderIntelligenceService(
                document_repo=TenderDocumentRepository(session),
                chunk_repo=DocumentChunkRepository(session),
                report_repo=TenderIntelligenceReportRepository(session),
                groq_client=GroqClient()
            )

            try:
                # Get all pending documents
                pending_documents = await intelligence_service._document_repo.get_pending(company_id)

                processed_count = 0
                failed_count = 0

                for document in pending_documents:
                    try:
                        await intelligence_service.process_document(
                            document.id, UUID(company_id), f"batch-{document.id}"
                        )
                        processed_count += 1
                    except Exception as e:
                        logger.error(
                            "batch_document_processing_failed",
                            document_id=str(document.id),
                            company_id=company_id,
                            error=str(e)
                        )
                        failed_count += 1

                logger.info(
                    "batch_document_processing_completed",
                    company_id=company_id,
                    total_documents=len(pending_documents),
                    processed_count=processed_count,
                    failed_count=failed_count
                )

                return {
                    "status": "completed",
                    "company_id": company_id,
                    "total_documents": len(pending_documents),
                    "processed_count": processed_count,
                    "failed_count": failed_count,
                    "success_rate": (processed_count / len(pending_documents)) * 100 if pending_documents else 0,
                    "completed_at": datetime.utcnow().isoformat()
                }

            except Exception as exc:
                logger.error(
                    "batch_processing_task_failed",
                    company_id=company_id,
                    error=str(exc),
                    retry_count=self.request.retries
                )

                # Retry if we have attempts left
                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=600, exc=exc)

                return {
                    "status": "failed",
                    "company_id": company_id,
                    "error": str(exc),
                    "retry_count": self.request.retries,
                    "failed_at": datetime.utcnow().isoformat()
                }

    import asyncio
    return asyncio.run(_batch_process())


@celery_app.task(
    bind=True,
    name="tender_intelligence.retry_failed_processing",
    max_retries=2,
    default_retry_delay=300
)
def retry_failed_processing_task(self, company_id: str) -> dict:
    """Retry processing of failed documents."""
    async def _retry_failed():
        async with get_async_session() as session:
            # Initialize service
            intelligence_service = TenderIntelligenceService(
                document_repo=TenderDocumentRepository(session),
                chunk_repo=DocumentChunkRepository(session),
                report_repo=TenderIntelligenceReportRepository(session),
                groq_client=GroqClient()
            )

            try:
                # Retry failed documents
                retried_documents = await intelligence_service.retry_failed_processing(
                    UUID(company_id), f"retry-{company_id}"
                )

                logger.info(
                    "failed_processing_retry_completed",
                    company_id=company_id,
                    retried_count=len(retried_documents)
                )

                return {
                    "status": "completed",
                    "company_id": company_id,
                    "retried_count": len(retried_documents),
                    "retried_document_ids": [str(doc.id) for doc in retried_documents],
                    "completed_at": datetime.utcnow().isoformat()
                }

            except Exception as exc:
                logger.error(
                    "retry_failed_processing_task_error",
                    company_id=company_id,
                    error=str(exc),
                    retry_count=self.request.retries
                )

                # Retry if we have attempts left
                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=300, exc=exc)

                return {
                    "status": "failed",
                    "company_id": company_id,
                    "error": str(exc),
                    "retry_count": self.request.retries,
                    "failed_at": datetime.utcnow().isoformat()
                }

    import asyncio
    return asyncio.run(_retry_failed())


@celery_app.task(name="tender_intelligence.cleanup_old_chunks")
def cleanup_old_chunks_task() -> dict:
    """Clean up old document chunks to maintain database performance."""
    async def _cleanup_chunks():
        async with get_async_session() as session:
            chunk_repo = DocumentChunkRepository(session)

            # Delete chunks older than 90 days
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            deleted_count = await chunk_repo.delete_old_chunks(cutoff_date)

            logger.info(
                "old_chunks_cleaned",
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
    return asyncio.run(_cleanup_chunks())


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'batch-process-documents': {
        'task': 'tender_intelligence.batch_process_documents',
        'schedule': crontab(hour=1, minute=0),  # 1 AM daily - process all pending documents
    },
    'retry-failed-processing': {
        'task': 'tender_intelligence.retry_failed_processing',
        'schedule': crontab(hour=4, minute=0),  # 4 AM daily - retry failed documents
    },
    'cleanup-old-chunks': {
        'task': 'tender_intelligence.cleanup_old_chunks',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily - cleanup old chunks
    },
}

celery_app.conf.timezone = 'UTC'
