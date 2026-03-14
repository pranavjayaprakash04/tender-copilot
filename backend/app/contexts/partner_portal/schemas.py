from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class CAPartnerBase(BaseModel):
    """Base CA partner schema."""
    name: str
    email: EmailStr
    phone: str
    icai_number: str


class CAPartnerCreate(CAPartnerBase):
    """CA partner creation schema."""
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class CAPartnerResponse(CAPartnerBase):
    """CA partner response schema."""
    id: UUID
    subscription_tier: str
    managed_company_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ManagedCompanyBase(BaseModel):
    """Base managed company schema."""
    company_id: UUID
    ca_id: UUID
    access_level: str


class ManagedCompanyCreate(ManagedCompanyBase):
    """Managed company creation schema."""
    pass


class ManagedCompanyResponse(ManagedCompanyBase):
    """Managed company response schema."""
    id: UUID
    company_name: str
    active_bids: int
    pending_tenders: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkBidRequest(BaseModel):
    """Bulk bid request schema."""
    company_ids: list[UUID]
    tender_id: UUID


class BulkAlertRequest(BaseModel):
    """Bulk alert request schema."""
    company_ids: list[UUID]
    message: str
    alert_type: str


class CADashboardResponse(BaseModel):
    """CA dashboard response schema."""
    ca_id: UUID
    total_companies: int
    total_active_bids: int
    total_won_bids: int
    companies: list[ManagedCompanyResponse]
