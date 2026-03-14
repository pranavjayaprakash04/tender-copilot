from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import UUID as SQLAlchemyUUID
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class CAPartner(Base):
    """CA Partner model for managing Chartered Accountant partners."""
    __tablename__ = "ca_partners"

    id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4()
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    icai_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    subscription_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ca_partner"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    managed_companies: Mapped[list[CAManagedCompany]] = relationship(
        "CAManagedCompany", back_populates="ca_partner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"CAPartner(id={self.id}, name={self.name}, email={self.email})"


class CAManagedCompany(Base):
    """Join table for CA partners managing companies."""
    __tablename__ = "ca_managed_companies"

    id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4()
    )
    ca_id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID, ForeignKey("ca_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_level: Mapped[str] = mapped_column(String(50), nullable=False, default="full")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    ca_partner: Mapped[CAPartner] = relationship("CAPartner", back_populates="managed_companies")

    # Unique constraint on (ca_id, company_id)
    __table_args__ = (UniqueConstraint("ca_id", "company_id", name="uq_ca_company"),)

    def __repr__(self) -> str:
        return f"CAManagedCompany(id={self.id}, ca_id={self.ca_id}, company_id={self.company_id})"
