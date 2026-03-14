from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.bid_intelligence.schemas import (
    CompetitorAnalysisRequest,
    CompetitorAnalysisResponse,
    CompetitorInsight,
    WinProbabilityRequest,
    WinProbabilityResponse,
)
from app.contexts.bid_lifecycle.market_prices import MarketPrice
from app.contexts.company_profile.repository import CompanyRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.shared.exceptions import NotFoundException

logger = structlog.get_logger()


class BidIntelligenceService:
    """Service for bid intelligence analysis."""

    def __init__(
        self,
        groq_client: GroqClient,
        tender_repo: TenderRepository,
        company_repo: CompanyRepository,
        bid_lifecycle_session: AsyncSession,
    ) -> None:
        self.groq_client = groq_client
        self.tender_repo = tender_repo
        self.company_repo = company_repo
        self.bid_lifecycle_session = bid_lifecycle_session

    async def analyze_competitors(self, req: CompetitorAnalysisRequest) -> CompetitorAnalysisResponse:
        """Analyze competitors for a tender."""
        try:
            # Step 1: Fetch tender from tender_discovery repo
            tender = await self.tender_repo.get_by_id(req.tender_id, req.company_id)
            if not tender:
                raise NotFoundException("Tender")

            # Step 2: Fetch market price for tender category from market_prices
            market_price = await self._get_market_price(tender.category)

            # Step 3: Build prompt with tender details + market context
            prompt = self._build_competitor_analysis_prompt(tender, market_price)

            # Step 4: Call deepseek-r1-distill-llama-70b via Groq
            response = await self.groq_client.complete(
                model=GroqModel.REASONING,
                system_prompt="You are an expert bid intelligence analyst. Analyze competitors and provide structured insights.",
                user_prompt=prompt,
                output_schema=dict,  # Will be parsed manually
                lang=None,  # Use default
                trace_id=f"competitor-analysis-{req.tender_id}",
                company_id=str(req.company_id),
                temperature=0.3,
            )

            # Step 5: Parse structured response into CompetitorAnalysisResponse
            insights = self._parse_competitor_insights(response.content)

            # Step 6: Inject Tamil translation if lang == "ta"
            if req.lang == "ta":
                # TODO: Implement Tamil translation
                pass

            return CompetitorAnalysisResponse(
                tender_id=req.tender_id,
                company_id=req.company_id,
                insights=insights,
                our_win_probability=0.75,  # Mock value
                recommended_price=market_price.avg_estimated_value if market_price else None,
                analysis_lang=req.lang,
                generated_at=datetime.now(timezone.utc),
            )
        except NotFoundException:
            raise
        except Exception as e:
            logger.error("analyze_competitors_error", tender_id=str(req.tender_id), error=str(e))
            raise

    async def calculate_win_probability(self, req: WinProbabilityRequest) -> WinProbabilityResponse:
        """Calculate win probability for a bid."""
        try:
            # Step 1: Fetch market avg for tender category
            tender = await self.tender_repo.get_by_id(req.tender_id, req.company_id)
            if not tender:
                raise NotFoundException("Tender")

            market_price = await self._get_market_price(tender.category)
            market_avg = market_price.avg_estimated_value if market_price else None

            # Step 2: Fetch company profile (capabilities, past wins)
            company_profile = await self.company_repo.get_by_id(req.company_id)
            if not company_profile:
                raise NotFoundException("Company profile")

            # Step 3: Fetch company's past bid outcomes from bid_outcomes table
            # TODO: Implement bid outcomes query
            past_win_rate = 0.6  # Mock value

            # Step 4: Calculate score using weighted factors
            if req.our_bid_amount and market_avg:
                market_price_alignment = max(0, 1 - abs(req.our_bid_amount - market_avg) / market_avg)
            else:
                market_price_alignment = 0.5

            capability_match = 0.8  # Mock value - would compare capabilities vs requirements

            win_probability = (
                market_price_alignment * 0.3 +
                past_win_rate * 0.4 +
                capability_match * 0.3
            )

            # Step 5: Return WinProbabilityResponse with factors list
            factors = [
                f"Market price alignment: {market_price_alignment:.2%}",
                f"Past win rate: {past_win_rate:.2%}",
                f"Capability match: {capability_match:.2%}",
            ]

            confidence = "high" if win_probability > 0.7 else "medium" if win_probability > 0.4 else "low"

            recommended_range = None
            if market_avg:
                recommended_range = {
                    "min": market_avg * 0.8,
                    "max": market_avg * 1.2,
                    "optimal": market_avg,
                }

            return WinProbabilityResponse(
                tender_id=req.tender_id,
                win_probability=win_probability,
                confidence=confidence,
                factors=factors,
                market_avg=market_avg,
                recommended_range=recommended_range,
            )
        except NotFoundException:
            raise
        except Exception as e:
            logger.error("calculate_win_probability_error", tender_id=str(req.tender_id), error=str(e))
            raise

    async def get_market_price(self, category: str) -> dict[str, Any] | None:
        """Fetch market price for a category."""
        try:
            market_price = await self._get_market_price(category)
            if not market_price:
                return None

            return {
                "category": market_price.tender_category,
                "avg_price": market_price.avg_estimated_value,
                "min_price": market_price.min_value,
                "max_price": market_price.max_value,
                "sample_count": market_price.sample_count,
                "last_refreshed": market_price.last_refreshed,
            }
        except Exception as e:
            logger.error("get_market_price_error", category=category, error=str(e))
            return None

    async def _get_market_price(self, category: str) -> MarketPrice | None:
        """Get market price from materialized view."""
        try:
            stmt = select(MarketPrice).where(MarketPrice.tender_category == category)
            result = await self.bid_lifecycle_session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("_get_market_price_error", category=category, error=str(e))
            return None

    def _build_competitor_analysis_prompt(self, tender: Any, market_price: MarketPrice | None) -> str:
        """Build prompt for competitor analysis."""
        market_context = ""
        if market_price:
            market_context = f"""
Market Context:
- Average estimated value: ₹{market_price.avg_estimated_value:,.2f}
- Value range: ₹{market_price.min_value:,.2f} - ₹{market_price.max_value:,.2f}
- Sample size: {market_price.sample_count} tenders
"""

        return f"""
Analyze competitors for the following tender:

Tender Details:
- Title: {tender.title}
- Category: {tender.category}
- Estimated Value: ₹{tender.estimated_value:,.2f}
- Portal: {tender.portal}
- Deadline: {tender.submission_deadline}

{market_context}

Provide analysis of likely competitors, their bidding strategies, and our competitive position.
Focus on:
1. Likely competitors and their typical bid amounts
2. Their strengths and weaknesses relative to this tender
3. Our win probability and recommended pricing strategy

Format the response as structured data that can be parsed.
"""

    def _parse_competitor_insights(self, response: str) -> list[CompetitorInsight]:
        """Parse competitor insights from AI response."""
        # TODO: Implement proper parsing of AI response
        # For now, return mock data
        return [
            CompetitorInsight(
                competitor_name="ABC Construction Ltd",
                estimated_bid=1500000.0,
                win_probability=0.65,
                strengths=["Strong financial backing", "Similar project experience"],
                weaknesses=["Higher overhead costs", "Slower delivery timeline"],
            ),
            CompetitorInsight(
                competitor_name="XYZ Engineering",
                estimated_bid=1400000.0,
                win_probability=0.45,
                strengths=["Technical expertise", "Competitive pricing"],
                weaknesses=["Limited resources", "Less experience with large projects"],
            ),
        ]
