from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class CompanySize(StrEnum):
    """Company size categories."""
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"

class Company(Base):
    """Company profile model."""
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=func.uuid_generate_v4())

    # User reference — links company to auth user
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    size: Mapped[CompanySize] = mapped_column(String(20), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)

    # Contact information
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Company details
    capabilities_text: Mapped[str] = mapped_column(Text, nullable=False)
    established_year: Mapped[int] = mapped_column(Integer, nullable=True)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=True)
    annual_revenue: Mapped[float] = mapped_column(Float, nullable=True)

    # Indian compliance fields
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    udyam_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    turnover_range: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Metadata
    certifications: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    specializations: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    past_projects: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    tender_matches: Mapped[list[Any]] = relationship("TenderMatch", back_populates="company")
    embedding: Mapped[Any] = relationship("CompanyEmbedding", back_populates="company", uselist=False)
    vault_documents: Mapped[list[Any]] = relationship("VaultDocument", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Company(id={self.id}, name={self.name}, industry={self.industry})"
