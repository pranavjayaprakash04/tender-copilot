"""Tender matching repository."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.tender_matching.models import (
    CompanyEmbedding,
    TenderEmbedding,
    TenderMatch,
)


class TenderMatchRepository:
    """Repository for tender match operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_similar_tenders(
        self,
        company_embedding: list[float],
        limit: int,
        min_score: float,
        trace_id: str | None = None
    ) -> list[TenderMatch]:
        """Find similar tenders using stored match scores (pgvector not available)."""
        result = await self._session.execute(
            select(TenderMatch)
            .where(TenderMatch.match_score >= min_score)
            .order_by(TenderMatch.match_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_similar_companies(
        self,
        tender_embedding: list[float],
        limit: int,
        min_score: float,
        trace_id: str | None = None
    ) -> list[TenderMatch]:
        """Find similar companies using stored match scores (pgvector not available)."""
        result = await self._session.execute(
            select(TenderMatch)
            .where(TenderMatch.match_score >= min_score)
            .order_by(TenderMatch.match_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def calculate_cosine_similarity(
        self,
        company_embedding: list[float],
        tender_embedding: list[float],
        trace_id: str | None = None
    ) -> float:
        """Calculate cosine similarity between two embeddings in Python."""
        if not company_embedding or not tender_embedding:
            return 0.0
        dot_product = sum(a * b for a, b in zip(company_embedding, tender_embedding))
        mag_a = sum(a * a for a in company_embedding) ** 0.5
        mag_b = sum(b * b for b in tender_embedding) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot_product / (mag_a * mag_b)

    async def get_by_id(self, match_id: UUID) -> TenderMatch | None:
        """Get match record by ID."""
        result = await self._session.execute(
            select(TenderMatch).where(TenderMatch.id == match_id)
        )
        return result.scalar_one_or_none()

    async def create(self, match_data: dict[str, Any]) -> TenderMatch:
        """Create a match record."""
        match = TenderMatch(**match_data)
        self._session.add(match)
        await self._session.commit()
        await self._session.refresh(match)
        return match


class CompanyEmbeddingRepository:
    """Repository for company embedding operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_company_id(self, company_id: UUID) -> CompanyEmbedding | None:
        """Get company embedding by company ID."""
        result = await self._session.execute(
            select(CompanyEmbedding).where(CompanyEmbedding.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        company_id: UUID,
        embedding: list[float],
        capabilities_text: str,
        processing_time_ms: int,
        trace_id: str | None = None
    ) -> CompanyEmbedding:
        """Create or update company embedding."""
        existing = await self.get_by_company_id(company_id)
        if existing:
            existing.capabilities_embedding = embedding
            existing.capabilities_text = capabilities_text
            existing.processing_time_ms = processing_time_ms
            existing.text_length = len(capabilities_text)
            existing.word_count = len(capabilities_text.split())
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        company_embedding = CompanyEmbedding(
            company_id=company_id,
            capabilities_embedding=embedding,
            capabilities_text=capabilities_text,
            processing_time_ms=processing_time_ms,
            text_length=len(capabilities_text),
            word_count=len(capabilities_text.split()),
        )
        self._session.add(company_embedding)
        await self._session.commit()
        await self._session.refresh(company_embedding)
        return company_embedding


class TenderEmbeddingRepository:
    """Repository for tender embedding operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_tender_id(self, tender_id: UUID) -> TenderEmbedding | None:
        """Get tender embedding by tender ID."""
        result = await self._session.execute(
            select(TenderEmbedding).where(TenderEmbedding.tender_id == tender_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        tender_id: UUID,
        embedding: list[float],
        requirements_text: str,
        processing_time_ms: int,
        trace_id: str | None = None
    ) -> TenderEmbedding:
        """Create or update tender embedding."""
        existing = await self.get_by_tender_id(tender_id)
        if existing:
            existing.requirements_embedding = embedding
            existing.requirements_text = requirements_text
            existing.processing_time_ms = processing_time_ms
            existing.text_length = len(requirements_text)
            existing.word_count = len(requirements_text.split())
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        tender_embedding = TenderEmbedding(
            tender_id=tender_id,
            requirements_embedding=embedding,
            requirements_text=requirements_text,
            processing_time_ms=processing_time_ms,
            text_length=len(requirements_text),
            word_count=len(requirements_text.split()),
        )
        self._session.add(tender_embedding)
        await self._session.commit()
        await self._session.refresh(tender_embedding)
        return tender_embedding
