from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.tender_discovery.models import Tender
from app.shared.exceptions import NotFoundException

from .models import DocumentChunk, TenderDocument

logger = structlog.get_logger()

class TenderDocumentRepository:
    """Repository for tender documents."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_tender_id(self, tender_id: UUID, company_id: UUID) -> TenderDocument | None:
        """Get document by tender ID."""
        stmt = select(TenderDocument).where(
            TenderDocument.tender_id == tender_id,
            TenderDocument.company_id == company_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class DocumentChunkRepository:
    """Repository for document chunks."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_document(self, document_id: UUID, company_id: UUID) -> list[DocumentChunk]:
        """Get chunks by document ID."""
        stmt = select(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.company_id == company_id
        ).order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TenderIntelligenceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tender_by_id(self, tender_id: UUID, company_id: UUID) -> Tender:
        """Get tender by ID scoped to company."""
        stmt = select(Tender).where(
            Tender.id == tender_id,
            Tender.company_id == company_id
        )
        result = await self.session.execute(stmt)
        tender = result.scalar_one_or_none()

        if not tender:
            logger.warning(
                "Tender not found",
                tender_id=str(tender_id),
                company_id=str(company_id)
            )
            raise NotFoundException(f"Tender {tender_id} not found")

        return tender

    async def get_tender_document_path(self, tender_id: UUID) -> str | None:
        """Get document path for tender."""
        stmt = select(Tender.document_path).where(Tender.id == tender_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
