"""Tender matching schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TenderMatchCreate(BaseModel):
    """Schema for creating tender match."""
    company_id: UUID
    tender_id: UUID
    match_score: float = Field(ge=0.0, le=1.0)
    confidence_level: str
    match_reasons: list[str] = []
    gap_analysis: dict[str, Any] = {}
    recommendations: list[str] = []
    industry_match: float = Field(ge=0.0, le=1.0)
    size_match: float = Field(ge=0.0, le=1.0)
    location_match: float = Field(ge=0.0, le=1.0)
    value_match: float = Field(ge=0.0, le=1.0)
    experience_match: float = Field(ge=0.0, le=1.0)
