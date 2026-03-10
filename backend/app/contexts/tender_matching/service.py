from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

import structlog
from sentence_transformers import SentenceTransformer

from app.contexts.company_profile.repository import CompanyRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.contexts.tender_matching.models import (
    CompanyEmbedding,
    TenderEmbedding,
    TenderMatch,
)
from app.contexts.tender_matching.repository import (
    CompanyEmbeddingRepository,
    TenderEmbeddingRepository,
    TenderMatchRepository,
)
from app.contexts.tender_matching.schemas import (
    TenderMatchCreate,
)
from app.shared.exceptions import NotFoundException, ValidationException

logger = structlog.get_logger()

# Initialize sentence transformer model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


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
        """Generate and store tender requirement embedding."""
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

    async def find_matches_for_company(
        self,
        company_id: UUID,
        limit: int = 50,
        min_score: float = 0.3,
        trace_id: str | None = None
    ) -> list[TenderMatch]:
        """Find matching tenders for a company using pgvector cosine similarity."""
        # Ensure company embedding exists
        company_embedding = await self.generate_company_embedding(company_id, trace_id=trace_id)

        # Use pgvector to find similar tenders
        matches = await self._match_repo.find_similar_tenders(
            company_embedding=company_embedding.capabilities_embedding,
            limit=limit,
            min_score=min_score,
            trace_id=trace_id
        )

        logger.info(
            "tender_matches_found",
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
        """Find matching companies for a tender using pgvector cosine similarity."""
        # Ensure tender embedding exists
        tender_embedding = await self.generate_tender_embedding(tender_id, trace_id=trace_id)

        # Use pgvector to find similar companies
        matches = await self._match_repo.find_similar_companies(
            tender_embedding=tender_embedding.requirements_embedding,
            limit=limit,
            min_score=min_score,
            trace_id=trace_id
        )

        logger.info(
            "company_matches_found",
            trace_id=trace_id,
            tender_id=tender_id,
            matches_count=len(matches),
            min_score=min_score
        )

        return matches

    async def calculate_cosine_similarity(
        self,
        company_id: UUID,
        tender_id: UUID,
        trace_id: str | None = None
    ) -> float:
        """Calculate cosine similarity between company and tender."""
        # Get embeddings
        company_embedding = await self._company_embedding_repo.get_by_company_id(company_id)
        tender_embedding = await self._tender_embedding_repo.get_by_tender_id(tender_id)

        if not company_embedding or not tender_embedding:
            raise ValidationException("Both company and tender must have embeddings")

        # Calculate cosine similarity using pgvector
        similarity = await self._match_repo.calculate_cosine_similarity(
            company_embedding.capabilities_embedding,
            tender_embedding.requirements_embedding,
            trace_id
        )

        logger.info(
            "cosine_similarity_calculated",
            trace_id=trace_id,
            company_id=company_id,
            tender_id=tender_id,
            similarity=similarity
        )

        return similarity

    async def create_match_record(
        self,
        company_id: UUID,
        tender_id: UUID,
        trace_id: str | None = None
    ) -> TenderMatch:
        """Create a detailed match record with analysis."""
        # Calculate similarity
        similarity = await self.calculate_cosine_similarity(company_id, tender_id, trace_id)

        # Get additional match criteria
        company = await self._company_repo.get_by_id(company_id)
        tender = await self._tender_repo.get_by_id(tender_id)

        # Calculate additional scores
        industry_score = self._calculate_industry_match(company, tender)
        size_score = self._calculate_size_match(company, tender)
        location_score = self._calculate_location_match(company, tender)
        value_score = self._calculate_value_match(company, tender)
        experience_score = self._calculate_experience_match(company, tender)

        # Generate match reasons and recommendations using GroqModel.FAST
        match_analysis = await self._generate_match_analysis(
            company, tender, similarity, trace_id
        )

        # Create match record
        match_data = TenderMatchCreate(
            company_id=company_id,
            tender_id=tender_id,
            match_score=similarity,
            confidence_level=self._determine_confidence_level(similarity),
            match_reasons=match_analysis.get("reasons", []),
            gap_analysis=match_analysis.get("gaps", {}),
            recommendations=match_analysis.get("recommendations", []),
            industry_match=industry_score,
            size_match=size_score,
            location_match=location_score,
            value_match=value_score,
            experience_match=experience_score
        )

        match = await self._match_repo.create(match_data)

        logger.info(
            "match_record_created",
            trace_id=trace_id,
            company_id=company_id,
            tender_id=tender_id,
            match_score=similarity,
            confidence_level=match.confidence_level
        )

        return match

    def _prepare_company_capabilities_text(self, company: Any) -> str:
        """Prepare company capabilities text for embedding."""
        parts = []

        # Basic company info
        if company.name:
            parts.append(f"Company: {company.name}")
        if company.description:
            parts.append(f"Description: {company.description}")
        if company.industry:
            parts.append(f"Industry: {company.industry}")

        # Capabilities and specializations
        if hasattr(company, 'capabilities_text') and company.capabilities_text:
            parts.append(f"Capabilities: {company.capabilities_text}")

        if hasattr(company, 'specializations') and company.specializations:
            parts.append(f"Specializations: {', '.join(company.specializations)}")

        # Experience and projects
        if hasattr(company, 'past_projects') and company.past_projects:
            projects_text = "Past Projects: "
            for project in company.past_projects[:5]:  # Limit to 5 projects
                if isinstance(project, dict):
                    projects_text += f"{project.get('title', '')} - {project.get('description', '')}; "
            parts.append(projects_text)

        # Certifications
        if hasattr(company, 'certifications') and company.certifications:
            parts.append(f"Certifications: {', '.join(company.certifications)}")

        # Size and scale
        if hasattr(company, 'employee_count'):
            parts.append(f"Company Size: {company.employee_count} employees")
        if hasattr(company, 'annual_revenue'):
            parts.append(f"Annual Revenue: ${company.annual_revenue:,}")

        return " ".join(parts)

    def _prepare_tender_requirements_text(self, tender: Any) -> str:
        """Prepare tender requirements text for embedding."""
        parts = []

        # Basic tender info
        if tender.title:
            parts.append(f"Tender Title: {tender.title}")
        if tender.description:
            parts.append(f"Description: {tender.description}")
        if hasattr(tender, 'organization_name') and tender.organization_name:
            parts.append(f"Organization: {tender.organization_name}")

        # Requirements and scope
        if hasattr(tender, 'requirements') and tender.requirements:
            parts.append(f"Requirements: {tender.requirements}")
        if hasattr(tender, 'scope_of_work') and tender.scope_of_work:
            parts.append(f"Scope of Work: {tender.scope_of_work}")

        # Technical specifications
        if hasattr(tender, 'technical_specifications') and tender.technical_specifications:
            parts.append(f"Technical Specifications: {tender.technical_specifications}")

        # Category and classification
        if hasattr(tender, 'category') and tender.category:
            parts.append(f"Category: {tender.category}")
        if hasattr(tender, 'sub_category') and tender.sub_category:
            parts.append(f"Sub-category: {tender.sub_category}")

        # CPV codes
        if hasattr(tender, 'cpv_codes') and tender.cpv_codes:
            parts.append(f"CPV Codes: {', '.join(tender.cpv_codes)}")

        # Value and scale
        if hasattr(tender, 'tender_value') and tender.tender_value:
            parts.append(f"Tender Value: ${tender.tender_value:,}")
        if hasattr(tender, 'emd_amount') and tender.emd_amount:
            parts.append(f"EMD Amount: ${tender.emd_amount:,}")

        return " ".join(parts)

    async def _generate_match_analysis(
        self,
        company: Any,
        tender: Any,
        similarity_score: float,
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """Generate match analysis using GroqModel.FAST."""
        try:
            # Prepare prompt for analysis
            prompt = f"""
Analyze the match between this company and tender:

Company:
{self._prepare_company_capabilities_text(company)}

Tender:
{self._prepare_tender_requirements_text(tender)}

Similarity Score: {similarity_score:.3f}

Provide:
1. Top 3 reasons why this is a good match
2. Top 3 capability gaps
3. Top 3 recommendations to improve the bid

Return as JSON with keys: reasons, gaps, recommendations
"""

            result = await self._groq.complete(
                model=GroqModel.FAST,  # Use FAST model for speed
                system_prompt="You are an expert in tender-company matching analysis. Provide concise, actionable insights.",
                user_prompt=prompt,
                output_schema=dict,  # Simple dict output
                trace_id=trace_id or f"match-analysis-{company.id}-{tender.id}",
                company_id=str(company.id),
                temperature=0.3
            )

            return result if isinstance(result, dict) else {}

        except Exception as e:
            logger.warning(
                "match_analysis_failed",
                trace_id=trace_id,
                company_id=company.id,
                tender_id=tender.id,
                error=str(e)
            )
            return {
                "reasons": ["High similarity score"],
                "gaps": ["Analysis unavailable"],
                "recommendations": ["Review requirements carefully"]
            }

    def _determine_confidence_level(self, similarity_score: float) -> str:
        """Determine confidence level based on similarity score."""
        if similarity_score >= 0.8:
            return "high"
        elif similarity_score >= 0.6:
            return "medium"
        else:
            return "low"

    def _calculate_industry_match(self, company: Any, tender: Any) -> float:
        """Calculate industry compatibility score."""
        # Simple industry matching - can be enhanced
        if hasattr(company, 'industry') and hasattr(tender, 'category'):
            company_industry = company.industry.lower() if company.industry else ""
            tender_category = tender.category.lower() if tender.category else ""

            if company_industry and tender_category:
                # Simple keyword matching
                if company_industry in tender_category or tender_category in company_industry:
                    return 1.0
                # Check for partial matches
                common_words = set(company_industry.split()) & set(tender_category.split())
                if common_words:
                    return len(common_words) / max(len(company_industry.split()), len(tender_category.split()))

        return 0.5  # Default neutral score

    def _calculate_size_match(self, company: Any, tender: Any) -> float:
        """Calculate company size compatibility score."""
        if hasattr(company, 'employee_count') and hasattr(tender, 'tender_value'):
            # Simple logic: larger tenders require larger companies
            if tender.tender_value > 1000000:  # Large tender
                return min(1.0, company.employee_count / 100)
            elif tender.tender_value > 100000:  # Medium tender
                return min(1.0, company.employee_count / 50)
            else:  # Small tender
                return min(1.0, company.employee_count / 20)

        return 0.5  # Default neutral score

    def _calculate_location_match(self, company: Any, tender: Any) -> float:
        """Calculate geographic compatibility score."""
        # Simple location matching - can be enhanced with geolocation
        if hasattr(company, 'location') and hasattr(tender, 'location'):
            company_location = company.location.lower() if company.location else ""
            tender_location = tender.location.lower() if tender.location else ""

            if company_location and tender_location:
                if company_location == tender_location:
                    return 1.0
                elif company_location in tender_location or tender_location in company_location:
                    return 0.8

        return 0.5  # Default neutral score

    def _calculate_value_match(self, company: Any, tender: Any) -> float:
        """Calculate tender value compatibility score."""
        if hasattr(company, 'annual_revenue') and hasattr(tender, 'tender_value'):
            # Tender should be reasonable relative to company revenue
            ratio = tender.tender_value / company.annual_revenue if company.annual_revenue > 0 else 0

            # Ideal ratio is 5-20% of annual revenue
            if 0.05 <= ratio <= 0.2:
                return 1.0
            elif 0.02 <= ratio <= 0.5:
                return 0.8
            else:
                return 0.5

        return 0.5  # Default neutral score

    def _calculate_experience_match(self, company: Any, tender: Any) -> float:
        """Calculate experience compatibility score."""
        if hasattr(company, 'past_projects') and company.past_projects and hasattr(tender, 'category'):
            # Check if company has experience in similar categories
            tender_category = tender.category.lower() if tender.category else ""

            relevant_projects = 0
            for project in company.past_projects:
                if isinstance(project, dict):
                    project_title = project.get('title', '').lower()
                    project_desc = project.get('description', '').lower()

                    if tender_category in project_title or tender_category in project_desc:
                        relevant_projects += 1

            if relevant_projects > 0:
                return min(1.0, relevant_projects / len(company.past_projects))

        return 0.5  # Default neutral score
