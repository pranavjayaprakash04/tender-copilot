from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator


class CompetitorAnalysisRequest(BaseModel):
    tender_id: str
    company_id: UUID
    lang: str = "en"

    @field_validator('lang')
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in ["en", "ta"]:
            raise ValueError("Language must be 'en' or 'ta'")
        return v


class CompetitorInsight(BaseModel):
    competitor_name: str
    estimated_bid: float | None
    win_probability: float
    strengths: list[str]
    weaknesses: list[str]


class CompetitorAnalysisResponse(BaseModel):
    tender_id: str
    company_id: UUID
    insights: list[CompetitorInsight]
    our_win_probability: float
    recommended_price: float | None
    analysis_lang: str
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WinProbabilityRequest(BaseModel):
    tender_id: str
    company_id: UUID
    our_bid_amount: float | None = None


class WinProbabilityResponse(BaseModel):
    tender_id: str
    win_probability: float
    confidence: str
    factors: list[str]
    market_avg: float | None
    recommended_range: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)


class MarketPriceResponse(BaseModel):
    category: str
    avg_price: float
    min_price: float
    max_price: float
    sample_count: int
    last_refreshed: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Price Intelligence ────────────────────────────────────────────────────────

class PriceBand(BaseModel):
    label: str          # e.g. "Aggressive", "Competitive", "Safe", "Premium"
    min_pct: float      # lower bound as % of market avg  (e.g. 0.80)
    max_pct: float      # upper bound as % of market avg  (e.g. 0.95)
    win_rate_estimate: float   # 0–1
    description: str


class PriceIntelligenceRequest(BaseModel):
    tender_id: str
    company_id: UUID


class PriceIntelligenceResponse(BaseModel):
    tender_id: str

    # Core market numbers
    market_avg: float
    market_min: float
    market_max: float
    optimal_price: float        # 92 % of market avg
    sample_count: int

    # Score 0–100: how well the tender value sits vs optimal
    price_to_win_score: float
    tender_value: float | None  # the tender's own estimated value if available

    # Where the tender value sits in the min–max spectrum (0–1)
    market_position: float

    # Four standard price bands
    price_bands: list[PriceBand]

    # Plain-English insights
    insights: list[str]

    # Spread-based pseudo trend points (6 values normalised to 0–1)
    trend_points: list[float]

    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
