from __future__ import annotations

from typing import Literal
from uuid import UUID
from pydantic import BaseModel


# ─── Existing Schemas ──────────────────────────────────────────────────────────

class TenderExplainRequest(BaseModel):
    tender_id: UUID
    lang: str = "en"


class TenderExplainResponse(BaseModel):
    tender_id: UUID
    summary: str
    key_requirements: list[str]
    eligibility: list[str]
    red_flags: list[str]
    lang: str


class ClauseExtractionRequest(BaseModel):
    tender_id: UUID
    lang: str = "en"


class ClauseExtractionResponse(BaseModel):
    tender_id: UUID
    clauses: list[dict]
    lang: str


class RiskDetectionRequest(BaseModel):
    tender_id: UUID
    lang: str = "en"


class RiskDetectionResponse(BaseModel):
    tender_id: UUID
    risks: list[dict]
    risk_score: int
    lang: str


# ─── Document Checklist Schemas ────────────────────────────────────────────────

class ChecklistItem(BaseModel):
    id: str
    name: str
    description: str
    required: bool
    status: Literal["have", "missing", "unknown"]
    in_vault: bool
    notes: str | None = None


class DocumentChecklistRequest(BaseModel):
    tender_id: str
    tender_title: str
    tender_category: str | None = None
    estimated_value: float | None = None
    tender_location: str | None = None
    description: str | None = None
    lang: str = "en"


class DocumentChecklistResponse(BaseModel):
    tender_id: str
    checklist: list[ChecklistItem]
    total: int
    have_count: int
    missing_count: int
    readiness_score: int
    summary: str
