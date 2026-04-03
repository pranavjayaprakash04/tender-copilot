from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

import structlog
from celery import Task

from app.contexts.compliance_vault.models import VaultDocument
from app.contexts.compliance_vault.repository import VaultDocumentRepository
from app.database import AsyncSessionFactory
from app.infrastructure.celery_app import celery_app

logger = structlog.get_logger()


class DatabaseTask(Task):
    """Base task with database session management."""

    def on_success(self, _retval, task_id, _args, _kwargs):
        """Log successful task completion."""
        logger.info(
            "task_completed",
            task_id=task_id,
            task_name=self.name,
            result=_retval
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failure."""
        logger.error(
            "task_failed",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            traceback=str(einfo)
        )


@celery_app.task(base=DatabaseTask, bind=True)
def check_expiring_documents(_self) -> dict:
    """Check for documents expiring in the next 30 days and send alerts."""
    async def run_check():
        async with AsyncSessionFactory() as session:
            repo = VaultDocumentRepository(session)

            # Get all companies with expiring documents
            expiring_docs = await repo.get_expiring_soon_for_all_companies(days=30)

            alerts_sent = 0
            companies_alerted = set()

            for company_id, documents in expiring_docs.items():
                if company_id not in companies_alerted:
                    # Send alert for this company
                    await send_expiry_alert(company_id, documents)
                    alerts_sent += len(documents)
                    companies_alerted.add(company_id)

            return {
                "companies_alerted": len(companies_alerted),
                "alerts_sent": alerts_sent,
                "timestamp": datetime.utcnow().isoformat()
            }

    return asyncio.run(run_check())


async def send_expiry_alert(company_id: UUID, documents: list[VaultDocument]) -> None:
    """Send expiry alert for a company's documents."""
    try:
        # TODO: Implement alert sending via email/WhatsApp
        # For now, just log the alert
        document_details = [
            f"{doc.filename} (expires {doc.expires_at.strftime('%Y-%m-%d')})"
            for doc in documents
        ]

        logger.info(
            "expiry_alert_sent",
            company_id=company_id,
            document_count=len(documents),
            documents=document_details
        )

    except Exception as e:
        logger.error(
            "expiry_alert_failed",
            company_id=company_id,
            error=str(e)
        )
        raise


@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_expired_documents(_self) -> dict:
    """Archive or flag expired documents."""
    async def run_cleanup():
        async with AsyncSessionFactory() as session:
            repo = VaultDocumentRepository(session)

            # Get all expired documents
            expired_docs = await repo.get_expired_for_all_companies()

            documents_processed = 0
            companies_affected = set()

            for company_id, documents in expired_docs.items():
                for doc in documents:
                    # Mark as expired (could also archive to cold storage)
                    doc.is_current = False
                    documents_processed += 1
                    companies_affected.add(company_id)

                await session.commit()

            return {
                "companies_affected": len(companies_affected),
                "documents_processed": documents_processed,
                "timestamp": datetime.utcnow().isoformat()
            }

    return asyncio.run(run_cleanup())


@celery_app.task(base=DatabaseTask, bind=True)
def generate_document_report(_self, company_id: str) -> dict:
    """Generate a comprehensive document report for a company."""
    async def run_report():
        async with AsyncSessionFactory() as session:
            repo = VaultDocumentRepository(session)
            company_uuid = UUID(company_id)

            # Get all document statistics
            stats = await repo.get_stats(company_uuid)

            # Get expiring soon documents
            expiring_soon = await repo.get_expiring_soon(company_uuid, 30)

            # Get expired documents
            expired = await repo.get_expired(company_uuid)

            # Get documents by type
            doc_type_counts = {}
            for doc_type in stats["by_type"]:
                docs = await repo.get_by_type(company_uuid, doc_type)
                doc_type_counts[doc_type] = len(docs)

            report = {
                "company_id": company_id,
                "generated_at": datetime.utcnow().isoformat(),
                "statistics": stats,
                "expiring_soon_count": len(expiring_soon),
                "expired_count": len(expired),
                "documents_by_type": doc_type_counts,
                "expiring_soon": [
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "doc_type": doc.doc_type,
                        "expires_at": doc.expires_at.isoformat() if doc.expires_at else None,
                        "days_until_expiry": doc.days_until_expiry
                    }
                    for doc in expiring_soon
                ],
                "expired": [
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "doc_type": doc.doc_type,
                        "expired_at": doc.expires_at.isoformat() if doc.expires_at else None
                    }
                    for doc in expired
                ]
            }

            # TODO: Save report to storage or send via email
            logger.info(
                "document_report_generated",
                company_id=company_id,
                total_documents=stats["total_documents"],
                expiring_soon=len(expiring_soon),
                expired=len(expired)
            )

            return report

    return asyncio.run(run_report())


# Helper functions to extend repository
async def get_expiring_soon_for_all_companies(_repo: VaultDocumentRepository, _days: int = 30) -> dict[UUID, list[VaultDocument]]:
    """Get expiring documents for all companies."""
    # This would need to be implemented in the repository
    # For now, return empty dict
    return {}

async def get_expired_for_all_companies(_repo: VaultDocumentRepository) -> dict[UUID, list[VaultDocument]]:
    """Get expired documents for all companies."""
    # This would need to be implemented in the repository
    # For now, return empty dict
    return {}
