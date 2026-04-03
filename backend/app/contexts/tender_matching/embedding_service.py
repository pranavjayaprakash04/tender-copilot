from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from app.contexts.company_profile.repository import CompanyProfileRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.contexts.tender_matching.models import (
    CompanyEmbedding,
    TenderEmbedding,
)
from app.contexts.tender_matching.repository import (
    CompanyEmbeddingRepository,
    TenderEmbeddingRepository,
)
from app.shared.exceptions import NotFoundException

logger = structlog.get_logger()

# Global variable for lazy-loaded model
_embedding_model = None

def get_embedding_model():
    """Get the sentence transformer model, loading it lazily."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


class EmbeddingService:
    """Service for generating and managing embeddings."""

    def __init__(
        self,
        company_embedding_repo: CompanyEmbeddingRepository,
        tender_embedding_repo: TenderEmbeddingRepository,
        company_repo: CompanyProfileRepository,
        tender_repo: TenderRepository,
    ) -> None:
        self._company_embedding_repo = company_embedding_repo
        self._tender_embedding_repo = tender_embedding_repo
        self._company_repo = company_repo
        self._tender_repo = tender_repo

    async def generate_company_embedding(
        self,
        company_id: UUID,
        force_refresh: bool = False,
        trace_id: str | None = None
    ) -> CompanyEmbedding:
        """Generate and store company capability embedding."""
        # Check if embedding already exists
        if not force_refresh:
            existing = await self._company_embedding_repo.get_by_company_id(company_id)
            if existing:
                logger.info(
                    "company_embedding_exists",
                    trace_id=trace_id,
                    company_id=company_id
                )
                return existing

        # Get company data
        company = await self._company_repo.get_by_id(company_id)
        if not company:
            raise NotFoundException("Company not found")

        # Prepare capabilities text
        capabilities_text = self._prepare_company_capabilities_text(company)

        # Generate embedding using sentence-transformers
        start_time = datetime.utcnow()
        embedding_model = get_embedding_model()
        embedding = embedding_model.encode(capabilities_text)
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Store embedding
        company_embedding = await self._company_embedding_repo.create_or_update(
            company_id=company_id,
            embedding=embedding,
            capabilities_text=capabilities_text,
            processing_time_ms=processing_time,
            trace_id=trace_id
        )

        logger.info(
            "company_embedding_generated",
            trace_id=trace_id,
            company_id=company_id,
            text_length=len(capabilities_text),
            processing_time_ms=processing_time
        )

        return company_embedding

    async def generate_tender_embedding(
        self,
        tender_id: UUID,
        force_refresh: bool = False,
        trace_id: str | None = None
    ) -> TenderEmbedding:
        """Generate and store tender requirements embedding."""
        # Check if embedding already exists
        if not force_refresh:
            existing = await self._tender_embedding_repo.get_by_tender_id(tender_id)
            if existing:
                logger.info(
                    "tender_embedding_exists",
                    trace_id=trace_id,
                    tender_id=tender_id
                )
                return existing

        # Get tender data
        tender = await self._tender_repo.get_by_id(tender_id)
        if not tender:
            raise NotFoundException("Tender not found")

        # Prepare requirements text
        requirements_text = self._prepare_tender_requirements_text(tender)

        # Generate embedding using sentence-transformers
        start_time = datetime.utcnow()
        embedding_model = get_embedding_model()
        embedding = embedding_model.encode(requirements_text)
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Store embedding
        tender_embedding = await self._tender_embedding_repo.create_or_update(
            tender_id=tender_id,
            embedding=embedding,
            requirements_text=requirements_text,
            processing_time_ms=processing_time,
            trace_id=trace_id
        )

        logger.info(
            "tender_embedding_generated",
            trace_id=trace_id,
            tender_id=tender_id,
            text_length=len(requirements_text),
            processing_time_ms=processing_time
        )

        return tender_embedding

    async def batch_embed_companies(
        self,
        company_ids: list[UUID] | None = None,
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """Generate embeddings for multiple companies in batch."""
        if company_ids is None:
            # Get all companies without embeddings
            companies = await self._company_repo.get_all_without_embeddings()
            company_ids = [company.id for company in companies]

        success_count = 0
        failed_count = 0
        errors = []

        for company_id in company_ids:
            try:
                await self.generate_company_embedding(company_id, force_refresh=False, trace_id=trace_id)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"Company {company_id}: {str(e)}")
                logger.error(
                    "batch_company_embedding_failed",
                    trace_id=trace_id,
                    company_id=company_id,
                    error=str(e)
                )

        logger.info(
            "batch_company_embedding_completed",
            trace_id=trace_id,
            total_companies=len(company_ids),
            success_count=success_count,
            failed_count=failed_count
        )

        return {
            "total_companies": len(company_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors,
            "completed_at": datetime.utcnow().isoformat()
        }

    async def batch_embed_tenders(
        self,
        tender_ids: list[UUID] | None = None,
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """Generate embeddings for multiple tenders in batch."""
        if tender_ids is None:
            # Get all tenders without embeddings
            tenders = await self._tender_repo.get_all_without_embeddings()
            tender_ids = [tender.id for tender in tenders]

        success_count = 0
        failed_count = 0
        errors = []

        for tender_id in tender_ids:
            try:
                await self.generate_tender_embedding(tender_id, force_refresh=False, trace_id=trace_id)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"Tender {tender_id}: {str(e)}")
                logger.error(
                    "batch_tender_embedding_failed",
                    trace_id=trace_id,
                    tender_id=tender_id,
                    error=str(e)
                )

        logger.info(
            "batch_tender_embedding_completed",
            trace_id=trace_id,
            total_tenders=len(tender_ids),
            success_count=success_count,
            failed_count=failed_count
        )

        return {
            "total_tenders": len(tender_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors,
            "completed_at": datetime.utcnow().isoformat()
        }

    def _prepare_company_capabilities_text(self, company: Any) -> str:
        """Prepare company capabilities text for embedding."""
        parts = []

        # Basic company info
        if company.name:
            parts.append(f"Company: {company.name}")

        if company.industry:
            parts.append(f"Industry: {company.industry}")

        if company.size:
            parts.append(f"Size: {company.size}")

        if company.location:
            parts.append(f"Location: {company.location}")

        # Capabilities and expertise
        if hasattr(company, 'capabilities_text') and company.capabilities_text:
            parts.append(f"Capabilities: {company.capabilities_text}")

        # Specializations
        if hasattr(company, 'specializations') and company.specializations:
            parts.append(f"Specializations: {', '.join(company.specializations)}")

        # Experience
        if hasattr(company, 'years_experience') and company.years_experience:
            parts.append(f"Experience: {company.years_experience} years")

        # Certifications
        if hasattr(company, 'certifications') and company.certifications:
            parts.append(f"Certifications: {', '.join(company.certifications)}")

        # Past projects
        if hasattr(company, 'past_projects') and company.past_projects:
            project_desc = []
            for project in company.past_projects[:5]:  # Limit to 5 projects
                if isinstance(project, dict):
                    project_desc.append(f"{project.get('name', '')}: {project.get('description', '')}")
                else:
                    project_desc.append(str(project))
            if project_desc:
                parts.append(f"Past Projects: {'; '.join(project_desc)}")

        return " ".join(parts)

    def _prepare_tender_requirements_text(self, tender: Any) -> str:
        """Prepare tender requirements text for embedding."""
        parts = []

        # Basic tender info
        if tender.title:
            parts.append(f"Title: {tender.title}")

        if tender.organization:
            parts.append(f"Organization: {tender.organization}")

        if tender.category:
            parts.append(f"Category: {tender.category}")

        if tender.state:
            parts.append(f"State: {tender.state}")

        # Requirements
        if hasattr(tender, 'description') and tender.description:
            parts.append(f"Description: {tender.description}")

        if hasattr(tender, 'requirements') and tender.requirements:
            parts.append(f"Requirements: {tender.requirements}")

        # Technical specifications
        if hasattr(tender, 'technical_specs') and tender.technical_specs:
            parts.append(f"Technical Specifications: {tender.technical_specs}")

        # Eligibility criteria
        if hasattr(tender, 'eligibility_criteria') and tender.eligibility_criteria:
            parts.append(f"Eligibility: {tender.eligibility_criteria}")

        # Scope of work
        if hasattr(tender, 'scope_of_work') and tender.scope_of_work:
            parts.append(f"Scope: {tender.scope_of_work}")

        # Timeline
        if hasattr(tender, 'submission_deadline') and tender.submission_deadline:
            parts.append(f"Deadline: {tender.submission_deadline}")

        # Value
        if hasattr(tender, 'estimated_value') and tender.estimated_value:
            parts.append(f"Value: {tender.estimated_value}")

        return " ".join(parts)
