from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import (
    UUID as SQLAlchemyUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class TenderSource(StrEnum):
    """Tender source portals."""
    CPPP = "cppp"
    EPROCURE = "eprocure"
    GEM = "gem"
    MSTC = "mstc"
    RAILWAYS = "railways"
    STATE_PORTAL = "state_portal"
    PSU = "psu"
    OTHER = "other"


class TenderCategory(StrEnum):
    """Tender categories."""
    CONSTRUCTION = "construction"
    SERVICES = "services"
    SUPPLY = "supply"
    IT_SOFTWARE = "it_software"
    MANUFACTURING = "manufacturing"
    CONSULTING = "consulting"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    TRANSPORTATION = "transportation"
    ENERGY = "energy"
    TELECOM = "telecom"
    AGRICULTURE = "agriculture"
    DEFENSE = "defense"
    OTHER = "other"


class TenderStatus(StrEnum):
    """Tender status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    BID_SUBMISSION_OPEN = "bid_submission_open"
    BID_SUBMISSION_CLOSED = "bid_submission_closed"
    EVALUATION = "evaluation"
    AWARDED = "awarded"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class TenderPriority(StrEnum):
    """Tender priority for matching."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Tender(Base):
    """Tender model for discovered tenders."""
    __tablename__ = "tenders"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic tender information
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Source information
    source: Mapped[TenderSource] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=True)

    # Classification
    category: Mapped[TenderCategory] = mapped_column(String(50), nullable=False)
    subcategory: Mapped[str] = mapped_column(String(100), nullable=True)
    priority: Mapped[TenderPriority] = mapped_column(String(20), nullable=False, default=TenderPriority.MEDIUM)

    # Financial information
    estimated_value: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    emd_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    processing_fee: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    # Timeline
    published_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bid_submission_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bid_opening_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tender_validity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_period: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status and metadata
    status: Mapped[TenderStatus] = mapped_column(String(50), nullable=False, default=TenderStatus.PUBLISHED)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Location information
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=True)
    pin_code: Mapped[str] = mapped_column(String(10), nullable=True)

    # Organization information
    procuring_entity: Mapped[str] = mapped_column(String(500), nullable=False)
    procuring_entity_type: Mapped[str] = mapped_column(String(100), nullable=True)

    # Additional details
    eligibility_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_and_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Scraping metadata
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    tender_matches: Mapped[list[Any]] = relationship("TenderMatch", back_populates="tender")
    embedding: Mapped[Any] = relationship("TenderEmbedding", back_populates="tender", uselist=False)

    def __repr__(self) -> str:
        return f"Tender(id={self.id}, tender_id={self.tender_id}, title={self.title[:50]}...)"

    @property
    def is_bid_submission_open(self) -> bool:
        return datetime.utcnow() < self.bid_submission_deadline and self.status in [
            TenderStatus.PUBLISHED, TenderStatus.BID_SUBMISSION_OPEN
        ]

    @property
    def days_until_deadline(self) -> int:
        delta = self.bid_submission_deadline - datetime.utcnow()
        return max(0, delta.days)

    @property
    def is_urgent(self) -> bool:
        return self.days_until_deadline <= 7 and self.is_bid_submission_open

    @property
    def is_closing_soon(self) -> bool:
        return self.days_until_deadline <= 3 and self.is_bid_submission_open


class TenderSearch(Base):
    """Tender search history and saved searches."""
    __tablename__ = "tender_searches"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    search_query: Mapped[str] = mapped_column(String(500), nullable=True)
    category: Mapped[TenderCategory | None] = mapped_column(String(50), nullable=True)
    min_value: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    max_value: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[TenderSource | None] = mapped_column(String(50), nullable=True)

    is_saved_search: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    search_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    alert_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"TenderSearch(id={self.id}, company_id={self.company_id}, query={self.search_query})"


class TenderAlert(Base):
    """Tender alerts for companies."""
    __tablename__ = "tender_alerts"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    # FK removed — tenders.id in Supabase is bigint, not UUID; stored as plain column
    tender_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, nullable=False, index=True)

    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    sent_via_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sent_via_whatsapp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"TenderAlert(id={self.id}, tender_id={self.tender_id}, type={self.alert_type})"
