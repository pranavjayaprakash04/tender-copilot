from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.bid_intelligence.consortium_schemas import (
    ConsortiumMatchRequest,
    ConsortiumMatchResponse,
    ConsortiumPartner,
)
from app.contexts.company_profile.repository import CompanyProfileRepository
from app.contexts.tender_discovery.repository import TenderRepository

logger = structlog.get_logger()


class ConsortiumService:
    """Service for consortium partner matching."""

    def __init__(
        self,
        company_repo: CompanyProfileRepository,
        tender_repo: TenderRepository,
        session: AsyncSession,
    ) -> None:
        self.company_repo = company_repo
        self.tender_repo = tender_repo
        self.session = session

    async def find_consortium_partners(self, req: ConsortiumMatchRequest) -> ConsortiumMatchResponse:
        """Find consortium partners for a tender."""
        try:
            # Step 1: Get required_capabilities from tender or request
            required_capabilities = req.required_capabilities
            if not required_capabilities:
                # Try to get from tender requirements
                tender = await self.tender_repo.get_by_id(req.tender_id, req.company_id)
                if tender and hasattr(tender, 'requirements'):
                    required_capabilities = tender.requirements or []
                else:
                    required_capabilities = []

            # Step 2: Query company_profiles for companies with matching capabilities
            # that are NOT the requesting company
            all_companies = await self.company_repo.get_all_companies()

            potential_partners = []
            for company in all_companies:
                if company.id == req.company_id:
                    continue  # Skip requesting company

                # Calculate capability overlap
                company_capabilities = company.capabilities or []
                matching_capabilities = self._calculate_capability_overlap(
                    required_capabilities, company_capabilities
                )

                if matching_capabilities:
                    match_score = len(matching_capabilities) / len(required_capabilities)

                    partner = ConsortiumPartner(
                        company_id=company.id,
                        company_name=company.name,
                        matching_capabilities=matching_capabilities,
                        match_score=match_score,
                        location=getattr(company, 'location', None),
                    )
                    potential_partners.append(partner)

            # Step 3: Score each match by capability overlap percentage
            potential_partners.sort(key=lambda x: x.match_score, reverse=True)

            # Step 4: Return top 5 matches sorted by score
            top_partners = potential_partners[:5]

            return ConsortiumMatchResponse(
                tender_id=req.tender_id,
                recommended_partners=top_partners,
                total_matches=len(top_partners),
            )
        except Exception as e:
            logger.error("find_consortium_partners_error", tender_id=str(req.tender_id), error=str(e))
            raise

    def _calculate_capability_overlap(
        self, required: list[str], available: list[str]
    ) -> list[str]:
        """Calculate overlap between required and available capabilities."""
        if not required or not available:
            return []

        # Normalize capabilities (case-insensitive comparison)
        required_normalized = [cap.lower().strip() for cap in required]
        available_normalized = [cap.lower().strip() for cap in available]

        # Find matches
        matches = []
        for req_cap in required_normalized:
            for avail_cap in available_normalized:
                if req_cap == avail_cap or req_cap in avail_cap or avail_cap in req_cap:
                    matches.append(avail_cap)
                    break

        return list(set(matches))  # Remove duplicates
