from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator


class CompanyProfileBase(BaseModel):
    name: str
    industry: str
    location: str                        # maps to state in UI
    contact_email: str
    contact_phone: str | None = None
    website: str | None = None
    description: str | None = None
    capabilities_text: str | None = None
    gstin: str | None = None
    udyam_number: str | None = None
    turnover_range: str | None = None
    preferred_lang: str = "en"

    model_config = ConfigDict(extra="ignore")   # ignore unknown fields gracefully

    @field_validator("preferred_lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in {"en", "ta"}:
            return "en"
        return v


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    location: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    description: str | None = None
    capabilities_text: str | None = None
    gstin: str | None = None
    udyam_number: str | None = None
    turnover_range: str | None = None
    preferred_lang: str | None = None

    model_config = ConfigDict(extra="ignore")

    @field_validator("preferred_lang")
    @classmethod
    def validate_lang(cls, v: str | None) -> str | None:
        if v is not None and v not in {"en", "ta"}:
            return "en"
        return v


class CompanyProfileResponse(BaseModel):
    id: UUID
    name: str
    industry: str
    location: str
    contact_email: str
    contact_phone: str | None = None
    website: str | None = None
    description: str | None = None
    capabilities_text: str | None = None
    gstin: str | None = None
    udyam_number: str | None = None
    turnover_range: str | None = None
    preferred_lang: str = "en"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="ignore")
