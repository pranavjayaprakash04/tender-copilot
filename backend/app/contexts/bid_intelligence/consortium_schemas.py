from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConsortiumMatchRequest(BaseModel):
    """Request for consortium partner matching."""
    tender_id: UUID
    company_id: UUID
    required_capabilities: list[str]


class ConsortiumPartner(BaseModel):
    """Potential consortium partner."""
    company_id: UUID
    company_name: str
    matching_capabilities: list[str]
    match_score: float
    location: str | None

    model_config = ConfigDict(from_attributes=True)


class ConsortiumMatchResponse(BaseModel):
    """Response with consortium partner matches."""
    tender_id: UUID
    recommended_partners: list[ConsortiumPartner]
    total_matches: int

    model_config = ConfigDict(from_attributes=True)
