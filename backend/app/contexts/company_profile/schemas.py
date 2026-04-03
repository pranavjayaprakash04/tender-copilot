from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class CompanyProfileBase(BaseModel):
    name: str
    gstin: str
    udyam_number: str | None = None
    state: str
    categories: list[str]
    capabilities: str | None = None
    preferred_lang: str = "en"
    turnover_range: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("preferred_lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        allowed = {"en", "ta"}
        if v not in allowed:
            raise ValueError(f"preferred_lang must be one of {allowed}")
        return v


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileUpdate(BaseModel):
    name: str | None = None
    gstin: str | None = None
    udyam_number: str | None = None
    state: str | None = None
    categories: list[str] | None = None
    capabilities: str | None = None
    preferred_lang: str | None = None
    turnover_range: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("preferred_lang")
    @classmethod
    def validate_lang(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = {"en", "ta"}
            if v not in allowed:
                raise ValueError(f"preferred_lang must be one of {allowed}")
        return v


class CompanyProfileResponse(CompanyProfileBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
