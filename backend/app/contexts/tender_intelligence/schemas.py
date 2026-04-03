from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class TenderExplainRequest(BaseModel):
    tender_id: UUID
    lang: str = "en"

    model_config = ConfigDict(extra="forbid")

    @field_validator("lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        allowed = {"en", "ta"}
        if v not in allowed:
            raise ValueError(f"lang must be one of {allowed}")
        return v


class TenderExplainResponse(BaseModel):
    tender_id: UUID
    summary: str
    key_requirements: list[str]
    eligibility: list[str]
    red_flags: list[str]
    lang: str

    model_config = ConfigDict(from_attributes=True)


class ClauseExtractionRequest(BaseModel):
    tender_id: UUID
    lang: str = "en"

    model_config = ConfigDict(extra="forbid")

    @field_validator("lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        allowed = {"en", "ta"}
        if v not in allowed:
            raise ValueError(f"lang must be one of {allowed}")
        return v


class ClauseExtractionResponse(BaseModel):
    tender_id: UUID
    clauses: list[dict]
    extracted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskDetectionRequest(BaseModel):
    tender_id: UUID
    lang: str = "en"

    model_config = ConfigDict(extra="forbid")

    @field_validator("lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        allowed = {"en", "ta"}
        if v not in allowed:
            raise ValueError(f"lang must be one of {allowed}")
        return v


class RiskDetectionResponse(BaseModel):
    tender_id: UUID
    risk_level: str
    risks: list[dict]
    lang: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v not in allowed:
            raise ValueError(f"risk_level must be one of {allowed}")
        return v
