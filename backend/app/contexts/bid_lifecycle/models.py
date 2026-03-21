from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text,
)
from sqlalchemy import UUID as SQLAlchemyUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class BidStatus(StrEnum):
    DRAFT = "draft"
    REVIEWING = "reviewing"
    SUBMITTED = "submitted"
    UNDER_EVALUATION = "under_evaluation"
    TECHNALLY_QUALIFIED = "technically_qualified"
    FINANCIALLY_QUALIFIED = "financially_qualified"
    AWARDED = "awarded"
    WON = "won"
    LOST = "lost"
    WITHDRAWN = "withdrawn"
    DISQUALIFIED = "disqualified"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class BidOutcome(StrEnum):
    WON = "won"
    LOST = "lost"
    WITHDRAWN = "withdrawn"
    DISQUALIFIED = "disqualified"
    CANCELLED = "cancelled"


class LossReason(StrEnum):
    PRICE_TOO_HIGH = "price_too_high"
    TECHNICAL_NON_COMPLIANCE = "technical_non_compliance"
    FINANCIAL_NON_COMPLIANCE = "financial_non_compliance"
    EXPERIENCE_INSUFFICIENT = "experience_insufficient"
    DOCUMENTATION_INCOMPLETE = "documentation_incomplete"
    LATE_SUBMISSION = "late_submission"
    EVALUATION_CRITERIA = "evaluation_criteria"
    PREFERRED_VENDOR = "preferred_vendor"
    OTHER = "other"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    FULLY_PAID = "fully_paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tender_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    bid_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bid_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    emd_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    bid_security_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    submission_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submission_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    award_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[BidStatus] = mapped_column(String(50), nullable=False, default=BidStatus.DRAFT)
    previous_status: Mapped[BidStatus | None] = mapped_column(String(50), nullable=True)
    lead_bidder: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bid_manager: Mapped[str | None] = mapped_column(String(200), nullable=True)
    technical_lead: Mapped[str | None] = mapped_column(String(200), nullable=True)
    compliance_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    financial_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    outcomes: Mapped[list[BidOutcomeRecord]] = relationship("BidOutcomeRecord", back_populates="bid", cascade="all, delete-orphan")
    payments: Mapped[list[BidPayment]] = relationship("BidPayment", back_populates="bid", cascade="all, delete-orphan")
    follow_ups: Mapped[list[BidFollowUp]] = relationship("BidFollowUp", back_populates="bid", cascade="all, delete-orphan")


class BidOutcomeRecord(Base):
    __tablename__ = "bid_outcomes"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    bid_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    outcome: Mapped[BidOutcome] = mapped_column(String(50), nullable=False)
    loss_reason: Mapped[LossReason | None] = mapped_column(String(50), nullable=True)
    loss_reason_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    winning_bidder: Mapped[str | None] = mapped_column(String(500), nullable=True)
    winning_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    competitor_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    our_ranking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    bid: Mapped[Bid] = relationship("Bid", back_populates="outcomes")


class BidPayment(Base):
    __tablename__ = "bid_payments"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    bid_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(String(50), nullable=False, default=PaymentStatus.PENDING)
    paid_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    paid_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    bid: Mapped[Bid] = relationship("Bid", back_populates="payments")


class BidFollowUp(Base):
    __tablename__ = "bid_follow_ups"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    bid_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_id: Mapped[UUID | None] = mapped_column(SQLAlchemyUUID, ForeignKey("bid_payments.id", ondelete="CASCADE"), nullable=True)
    follow_up_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    contact_person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_method: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    scheduled_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[Text] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    bid: Mapped[Bid] = relationship("Bid", back_populates="follow_ups")
    payment: Mapped[BidPayment | None] = relationship("BidPayment")


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    tender_category: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    avg_estimated_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    min_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    max_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_refreshed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
