from __future__ import annotations

from uuid import UUID

import structlog

from app.contexts.company_profile.repository import CompanyRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.contexts.tender_matching.embedding_service import EmbeddingService
from app.contexts.tender_matching.models import TenderMatch
from app.contexts.tender_matching.repository import (
    CompanyEmbeddingRepository,
    TenderEmbeddingRepository,
    TenderMatchRepository,
)
from app.shared.exceptions import ValidationException

logger = structlog.get_logger()


class TenderMatchingService:
    """Service for AI-powered tender-company matching using pgvector."""

    def __init__(
        self,
        match_repo: TenderMatchRepository,
        company_embedding_repo: CompanyEmbeddingRepository,
        tender_embedding_repo: TenderEmbeddingRepository,
        company_repo: CompanyRepository,
        tender_repo: TenderRepository,
    ) -> None:
        self._match_repo = match_repo
        self._company_embedding_repo = company_embedding_repo
        self._tender_embedding_repo = tender_embedding_repo
        self._company_repo = company_repo
        self._tender_repo = tender_repo
        self._embedding_service = EmbeddingService(
            company_embedding_repo,
            tender_embedding_repo,
            company_repo,
            tender_repo
        )

    async def find_matches_for_company(
        self,
        company_id: UUID,
        limit: int = 50,
        min_score: float = 0.3,
        trace_id: str | None = None
    ) -> list[TenderMatch]:
        """Find matching tenders for a company using similarity search."""
        # Ensure company has embedding
        company_embedding = await self._company_embedding_repo.get_by_company_id(company_id)
        if not company_embedding:
            raise ValidationException("Company must have embedding to find matches")

        # Perform similarity search
        matches = await self._match_repo.find_similar_tenders(
            company_embedding.capabilities_embedding,
            limit=limit,
            min_score=min_score,
            trace_id=trace_id
        )

        logger.info(
            "company_matches_found",
            trace_id=trace_id,
            company_id=company_id,
            matches_count=len(matches),
            min_score=min_score
        )

        return matches

    async def find_matches_for_tender(
        self,
        tender_id: UUID,
        limit: int = 50,
        min_score: float = 0.3,
        trace_id: str | None = None
    ) -> list[TenderMatch]:
        """Find matching companies for a tender using similarity search."""
        # Ensure tender has embedding
        tender_embedding = await self._tender_embedding_repo.get_by_tender_id(tender_id)
        if not tender_embedding:
            raise ValidationException("Tender must have embedding to find matches")

        # Perform similarity search
        matches = await self._match_repo.find_similar_companies(
            tender_embedding.requirements_embedding,
            limit=limit,
            min_score=min_score,
            trace_id=trace_id
        )

        logger.info(
            "tender_matches_found",
            trace_id=trace_id,
            tender_id=tender_id,
            matches_count=len(matches),
            min_score=min_score
        )

        return matches
