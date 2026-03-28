from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.bid_intelligence.schemas import (
    CompetitorAnalysisRequest,
    CompetitorAnalysisResponse,
    CompetitorInsight,
    WinProbabilityRequest,
    WinProbabilityResponse,
)
from app.contexts.bid_lifecycle.market_prices import MarketPrice
from app.contexts.company_profile.repository import CompanyProfileRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.infrastructure.groq_client import GroqClient

logger = structlog.get_logger()


class BidIntelligenceService:
    """Service for bid intelligence analysis."""

    def __init__(
        self,
        groq_client: GroqClient,
        tender_repo: TenderRepository,
        company_repo: CompanyProfileRepository,
        bid_lifecycle_session: AsyncSession,
    ) -> None:
        self.groq_client = groq_client
        self.tender_repo = tender_repo
        self.company_repo = company_repo
        self.session = bid_lifecycle_session

    async def _get_scraped_tender(self, tender_id: str) -> dict | None:
        """Fetch tender from scraped tenders table by integer ID."""
        try:
            result = await self.session.execute(
                text("""
                    SELECT id::text, tender_id, title, organization, category,
                           estimated_value, emd_amount, portal, location,
                           bid_end_date, status
                    FROM tenders
                    WHERE id::text = :tid
                    LIMIT 1
                """),
                {"tid": str(tender_id)}
            )
            row = result.mappings().first()
            return dict(row) if row else None
        except Exception as e:
            logger.error("get_scraped_tender_error", tender_id=tender_id, error=str(e))
            return None

    async def analyze_competitors(self, req: CompetitorAnalysisRequest) -> CompetitorAnalysisResponse:
        """Analyze competitors for a tender."""
        tender = await self._get_scraped_tender(req.tender_id)

        # Use mock competitor insights (real AI call can be wired later)
        insights = [
            CompetitorInsight(
                competitor_name="ABC Enterprises",
                estimated_bid=tender["estimated_value"] * 0.95 if tender and tender.get("estimated_value") else None,
                win_probability=0.65,
                strengths=["Strong financial backing", "Similar project experience"],
                weaknesses=["Higher overhead costs", "Slower delivery timeline"],
            ),
            CompetitorInsight(
                competitor_name="XYZ Solutions",
                estimated_bid=tender["estimated_value"] * 0.88 if tender and tender.get("estimated_value") else None,
                win_probability=0.45,
                strengths=["Technical expertise", "Competitive pricing"],
                weaknesses=["Limited resources", "Less experience with large projects"],
            ),
        ]

        recommended_price = None
        if tender and tender.get("estimated_value"):
            recommended_price = tender["estimated_value"] * 0.92

        return CompetitorAnalysisResponse(
            tender_id=req.tender_id,
            company_id=req.company_id,
            insights=insights,
            our_win_probability=0.72,
            recommended_price=recommended_price,
            analysis_lang=req.lang,
            generated_at=datetime.now(UTC),
        )

    async def calculate_win_probability(self, req: WinProbabilityRequest) -> WinProbabilityResponse:
        """Calculate win probability for a bid."""
        tender = await self._get_scraped_tender(req.tender_id)
        category = tender.get("category") if tender else None
        market_price = await self._get_market_price(category) if category else None
        market_avg = market_price.avg_estimated_value if market_price else None

        # Score calculation
        if req.our_bid_amount and market_avg:
            price_align = max(0.0, 1.0 - abs(req.our_bid_amount - market_avg) / market_avg)
        else:
            price_align = 0.5

        past_win_rate = 0.6
        capability_match = 0.8

        win_probability = round(price_align * 0.3 + past_win_rate * 0.4 + capability_match * 0.3, 3)
        confidence = "high" if win_probability > 0.7 else "medium" if win_probability > 0.4 else "low"

        factors = [
            f"Market price alignment: {price_align:.0%}",
            f"Historical win rate: {past_win_rate:.0%}",
            f"Capability match: {capability_match:.0%}",
        ]

        recommended_range = None
        if market_avg:
            recommended_range = {
                "min": round(market_avg * 0.80),
                "max": round(market_avg * 1.20),
                "optimal": round(market_avg * 0.92),
            }

        return WinProbabilityResponse(
            tender_id=req.tender_id,
            win_probability=win_probability,
            confidence=confidence,
            factors=factors,
            market_avg=market_avg,
            recommended_range=recommended_range,
        )

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
        """Get market price from market_prices table."""
        try:
            stmt = select(MarketPrice).where(MarketPrice.tender_category == category)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("_get_market_price_error", category=category, error=str(e))
            return None
