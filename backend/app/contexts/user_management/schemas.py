from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserBase(BaseModel):
    email: EmailStr
    role: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"msme_owner", "ca_partner"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters long")
        return v


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    subscription_tier: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(extra="forbid")


class SubscriptionResponse(BaseModel):
    user_id: UUID
    plan: str
    status: str
    renewal_date: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
