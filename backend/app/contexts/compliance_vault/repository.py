from __future__ import annotations

from datetime import datetime, timedelta, UTC
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contexts.compliance_vault.models import (
    DocumentType,
    VaultDocument,
    VaultDocumentMapping,
)
from app.contexts.compliance_vault.schemas import (
    DocumentSearchFilters,
    VaultDocumentCreate,
    VaultDocumentUpdate,
)
from app.shared.exceptions import NotFoundException


class VaultDocumentRepository:
    """Repository for vault document operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document_data: VaultDocumentCreate) -> VaultDocument:
        """Create a new vault document."""
        existing = await self._session.execute(
            select(VaultDocument).where(
                and_(
                    VaultDocument.company_id == document_data.company_id,
                    VaultDocument.doc_type == document_data.doc_type,
                    VaultDocument.filename == document_data.filename,
                    VaultDocument.is_current
                )
            )
        )
        existing_doc = existing.scalar_one_or_none()

        if existing_doc:
            existing_doc.is_current = False
            new_version = existing_doc.version + 1
        else:
            new_version = 1

        document = VaultDocument(
            company_id=document_data.company_id,
            doc_type=document_data.doc_type,
            filename=document_data.filename,
            storage_path="",  # Set after upload
            version=new_version,
            expires_at=document_data.expires_at,
            is_current=True
        )

        self._session.add(document)
        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def get_by_id(self, document_id: UUID, company_id: UUID) -> VaultDocument:
        """Get a document by ID — scoped to company (prevents cross-tenant access)."""
        result = await self._session.execute(
            select(VaultDocument).where(
                and_(
                    VaultDocument.id == document_id,
                    VaultDocument.company_id == company_id  # enforces tenant isolation
                )
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundException("Document")

        return document

    async def get_by_company(
        self,
        company_id: UUID,
        filters: DocumentSearchFilters | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[VaultDocument], int]:
        """Get documents for a company with optional filters."""
        # Fixed: use datetime.now(UTC) instead of deprecated datetime.utcnow()
        now = datetime.now(UTC)

        query = select(VaultDocument).where(VaultDocument.company_id == company_id)

        if filters:
            if filters.doc_types:
                query = query.where(VaultDocument.doc_type.in_(filters.doc_types))

            if filters.is_current is not None:
                query = query.where(VaultDocument.is_current == filters.is_current)

            if filters.is_expired is not None:
                if filters.is_expired:
                    query = query.where(
                        and_(VaultDocument.expires_at.is_not(None), VaultDocument.expires_at < now)
                    )
                else:
                    query = query.where(
                        or_(VaultDocument.expires_at.is_(None), VaultDocument.expires_at >= now)
                    )

            if filters.is_expiring_soon is not None:
                expiry_threshold = now + timedelta(days=30)
                if filters.is_expiring_soon:
                    query = query.where(
                        and_(
                            VaultDocument.expires_at.is_not(None),
                            VaultDocument.expires_at <= expiry_threshold,
                            VaultDocument.expires_at >= now
                        )
                    )
                else:
                    query = query.where(
                        or_(VaultDocument.expires_at.is_(None), VaultDocument.expires_at > expiry_threshold)
                    )

            if filters.date_from:
                query = query.where(VaultDocument.uploaded_at >= filters.date_from)

            if filters.date_to:
                query = query.where(VaultDocument.uploaded_at <= filters.date_to)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(desc(VaultDocument.uploaded_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def update(
        self,
        document_id: UUID,
        company_id: UUID,
        update_data: VaultDocumentUpdate
    ) -> VaultDocument:
        """Update a document."""
        document = await self.get_by_id(document_id, company_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(document, field, value)

        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def delete(self, document_id: UUID, company_id: UUID) -> None:
        """Delete a document."""
        document = await self.get_by_id(document_id, company_id)
        await self._session.delete(document)

    async def get_expiring_soon(self, company_id: UUID, days: int = 30) -> list[VaultDocument]:
        """Get documents expiring within specified days."""
        now = datetime.now(UTC)
        expiry_threshold = now + timedelta(days=days)

        result = await self._session.execute(
            select(VaultDocument).where(
                and_(
                    VaultDocument.company_id == company_id,
                    VaultDocument.expires_at.is_not(None),
                    VaultDocument.expires_at <= expiry_threshold,
                    VaultDocument.expires_at >= now,
                    VaultDocument.is_current
                )
            ).order_by(VaultDocument.expires_at)
        )

        return list(result.scalars().all())

    async def get_expired(self, company_id: UUID) -> list[VaultDocument]:
        """Get expired documents."""
        now = datetime.now(UTC)

        result = await self._session.execute(
            select(VaultDocument).where(
                and_(
                    VaultDocument.company_id == company_id,
                    VaultDocument.expires_at.is_not(None),
                    VaultDocument.expires_at < now,
                    VaultDocument.is_current
                )
            ).order_by(desc(VaultDocument.expires_at))
        )

        return list(result.scalars().all())

    async def get_by_type(self, company_id: UUID, doc_type: DocumentType) -> list[VaultDocument]:
        """Get current documents of a specific type."""
        result = await self._session.execute(
            select(VaultDocument).where(
                and_(
                    VaultDocument.company_id == company_id,
                    VaultDocument.doc_type == doc_type,
                    VaultDocument.is_current
                )
            ).order_by(desc(VaultDocument.uploaded_at))
        )
        return list(result.scalars().all())

    async def get_stats(self, company_id: UUID) -> dict:
        """Get document statistics for a company."""
        now = datetime.now(UTC)
        expiry_threshold = now + timedelta(days=30)

        total = (await self._session.execute(
            select(func.count(VaultDocument.id)).where(VaultDocument.company_id == company_id)
        )).scalar()

        current = (await self._session.execute(
            select(func.count(VaultDocument.id)).where(
                and_(VaultDocument.company_id == company_id, VaultDocument.is_current)
            )
        )).scalar()

        expired = (await self._session.execute(
            select(func.count(VaultDocument.id)).where(
                and_(
                    VaultDocument.company_id == company_id,
                    VaultDocument.expires_at.is_not(None),
                    VaultDocument.expires_at < now,
                    VaultDocument.is_current
                )
            )
        )).scalar()

        expiring_soon = (await self._session.execute(
            select(func.count(VaultDocument.id)).where(
                and_(
                    VaultDocument.company_id == company_id,
                    VaultDocument.expires_at.is_not(None),
                    VaultDocument.expires_at <= expiry_threshold,
                    VaultDocument.expires_at >= now,
                    VaultDocument.is_current
                )
            )
        )).scalar()

        by_type_result = await self._session.execute(
            select(VaultDocument.doc_type, func.count(VaultDocument.id))
            .where(and_(VaultDocument.company_id == company_id, VaultDocument.is_current))
            .group_by(VaultDocument.doc_type)
        )
        by_type = dict(by_type_result.all())

        return {
            "total_documents": total,
            "current_documents": current,
            "expired_documents": expired,
            "expiring_soon_documents": expiring_soon,
            "by_type": by_type
        }


class VaultDocumentMappingRepository:
    """Repository for document-tender mappings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_mapping(self, tender_id: UUID, document_id: UUID) -> VaultDocumentMapping:
        """Create a mapping between tender and document."""
        mapping = VaultDocumentMapping(tender_id=tender_id, vault_doc_id=document_id)
        self._session.add(mapping)
        await self._session.flush()
        await self._session.refresh(mapping)
        return mapping

    async def get_by_tender(self, tender_id: UUID, company_id: UUID) -> list[VaultDocument]:
        """Get all documents mapped to a tender — scoped to company to prevent cross-tenant leak."""
        # Fixed: added company_id filter — previously returned ANY company's docs for a tender
        result = await self._session.execute(
            select(VaultDocument)
            .join(VaultDocumentMapping, VaultDocumentMapping.vault_doc_id == VaultDocument.id)
            .where(
                and_(
                    VaultDocumentMapping.tender_id == tender_id,
                    VaultDocument.company_id == company_id  # tenant isolation enforced
                )
            )
        )
        return list(result.scalars().all())

    async def get_by_document(self, document_id: UUID) -> list[UUID]:
        """Get all tenders mapped to a document."""
        result = await self._session.execute(
            select(VaultDocumentMapping.tender_id)
            .where(VaultDocumentMapping.vault_doc_id == document_id)
        )
        return [row.tender_id for row in result.all()]

    async def remove_mapping(self, tender_id: UUID, document_id: UUID) -> None:
        """Remove a mapping between tender and document."""
        result = await self._session.execute(
            select(VaultDocumentMapping).where(
                and_(
                    VaultDocumentMapping.tender_id == tender_id,
                    VaultDocumentMapping.vault_doc_id == document_id
                )
            )
        )
        mapping = result.scalar_one_or_none()
        if mapping:
            await self._session.delete(mapping)
