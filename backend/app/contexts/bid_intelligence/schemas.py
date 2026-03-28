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
