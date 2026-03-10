from __future__ import annotations

from datetime import datetime
from enum import StrEnum
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
from sqlalchemy import UUID as SQLAlchemyUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class BidStatus(StrEnum):
    """Bid status with state machine transitions."""
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
    """Bid outcome categories."""
    WON = "won"
    LOST = "lost"
    WITHDRAWN = "withdrawn"
    DISQUALIFIED = "disqualified"
    CANCELLED = "cancelled"


class LossReason(StrEnum):
    """Reasons for bid loss."""
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
    """Payment status for awarded bids."""
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    FULLY_PAID = "fully_paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"


class Bid(Base):
    """Bid model with state machine for status transitions."""
    __tablename__ = "bids"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tender_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic bid information
    bid_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Financial information
    bid_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    emd_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    bid_security_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    # Timeline
    submission_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submission_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluation_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    award_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status and state machine
    status: Mapped[BidStatus] = mapped_column(String(50), nullable=False, default=BidStatus.DRAFT)
    previous_status: Mapped[BidStatus | None] = mapped_column(String(50), nullable=True)

    # Team and responsibility
    lead_bidder: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bid_manager: Mapped[str | None] = mapped_column(String(200), nullable=True)
    technical_lead: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Compliance and documents
    compliance_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    financial_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    outcomes: Mapped[list[BidOutcomeRecord]] = relationship("BidOutcomeRecord", back_populates="bid", cascade="all, delete-orphan")
    payments: Mapped[list[BidPayment]] = relationship("BidPayment", back_populates="bid", cascade="all, delete-orphan")
    follow_ups: Mapped[list[BidFollowUp]] = relationship("BidFollowUp", back_populates="bid", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Bid(id={self.id}, bid_number={self.bid_number}, status={self.status})"

    @property
    def can_edit(self) -> bool:
        """Check if bid can be edited."""
        return self.status in [BidStatus.DRAFT, BidStatus.REVIEWING]

    @property
    def can_submit(self) -> bool:
        """Check if bid can be submitted."""
        return self.status in [BidStatus.DRAFT, BidStatus.REVIEWING]

    @property
    def can_withdraw(self) -> bool:
        """Check if bid can be withdrawn."""
        return self.status in [BidStatus.DRAFT, BidStatus.REVIEWING, BidStatus.SUBMITTED]

    @property
    def is_final_status(self) -> bool:
        """Check if status is final (no further transitions possible)."""
        return self.status in [BidStatus.WON, BidStatus.LOST, BidStatus.WITHDRAWN, BidStatus.DISQUALIFIED, BidStatus.CANCELLED]

    @property
    def days_since_submission(self) -> int | None:
        """Get days since bid submission."""
        if not self.submission_date:
            return None
        delta = datetime.utcnow() - self.submission_date
        return delta.days

    @property
    def is_overdue_payment(self) -> bool:
        """Check if payment is overdue."""
        if self.status != BidStatus.WON:
            return False
        return any(payment.is_overdue for payment in self.payments)

    def get_allowed_transitions(self) -> list[BidStatus]:
        """Get allowed status transitions based on current state."""
        transitions = {
            BidStatus.DRAFT: [BidStatus.REVIEWING, BidStatus.SUBMITTED, BidStatus.CANCELLED],
            BidStatus.REVIEWING: [BidStatus.DRAFT, BidStatus.SUBMITTED, BidStatus.CANCELLED],
            BidStatus.SUBMITTED: [BidStatus.UNDER_EVALUATION, BidStatus.WITHDRAWN],
            BidStatus.UNDER_EVALUATION: [BidStatus.TECHNALLY_QUALIFIED, BidStatus.DISQUALIFIED, BidStatus.ON_HOLD],
            BidStatus.TECHNALLY_QUALIFIED: [BidStatus.FINANCIALLY_QUALIFIED, BidStatus.DISQUALIFIED],
            BidStatus.FINANCIALLY_QUALIFIED: [BidStatus.AWARDED, BidStatus.LOST],
            BidStatus.AWARDED: [BidStatus.WON],
            BidStatus.WON: [],  # Final state
            BidStatus.LOST: [],  # Final state
            BidStatus.WITHDRAWN: [],  # Final state
            BidStatus.DISQUALIFIED: [],  # Final state
            BidStatus.ON_HOLD: [BidStatus.UNDER_EVALUATION, BidStatus.WITHDRAWN],
            BidStatus.CANCELLED: [],  # Final state
        }
        return transitions.get(self.status, [])

    def can_transition_to(self, new_status: BidStatus) -> bool:
        """Check if transition to new status is allowed."""
        return new_status in self.get_allowed_transitions()


class BidOutcomeRecord(Base):
    """Record of bid outcomes with mandatory data for final statuses."""
    __tablename__ = "bid_outcomes"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    bid_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)

    # Outcome information
    outcome: Mapped[BidOutcome] = mapped_column(String(50), nullable=False)
    loss_reason: Mapped[LossReason | None] = mapped_column(String(50), nullable=True)
    loss_reason_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Competition information
    winning_bidder: Mapped[str | None] = mapped_column(String(500), nullable=True)
    winning_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    competitor_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    our_ranking: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Evaluation details
    technical_score_received: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    financial_score_received: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    total_score_received: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    max_possible_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Feedback and learning
    evaluation_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Financial analysis
    profit_margin: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    cost_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pricing_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    recorded_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    bid: Mapped[Bid] = relationship("Bid", back_populates="outcomes")

    def __repr__(self) -> str:
        return f"BidOutcomeRecord(id={self.id}, bid_id={self.bid_id}, outcome={self.outcome})"


class BidPayment(Base):
    """Payment tracking for awarded bids."""
    __tablename__ = "bid_payments"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    bid_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)

    # Payment information
    payment_type: Mapped[str] = mapped_column(String(50), nullable=False)  # advance, milestone, final, retention
    payment_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Status and tracking
    status: Mapped[PaymentStatus] = mapped_column(String(50), nullable=False, default=PaymentStatus.PENDING)
    paid_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    paid_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Payment details
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Follow-up tracking
    last_follow_up_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    follow_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_follow_up_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    bid: Mapped[Bid] = relationship("Bid", back_populates="payments")

    def __repr__(self) -> str:
        return f"BidPayment(id={self.id}, bid_id={self.bid_id}, amount={self.payment_amount})"

    @property
    def is_overdue(self) -> bool:
        """Check if payment is overdue."""
        if self.status in [PaymentStatus.FULLY_PAID, PaymentStatus.DISPUTED]:
            return False
        return datetime.utcnow() > self.due_date and self.status != PaymentStatus.FULLY_PAID

    @property
    def days_overdue(self) -> int:
        """Get days overdue."""
        if not self.is_overdue:
            return 0
        delta = datetime.utcnow() - self.due_date
        return delta.days

    @property
    def outstanding_amount(self) -> float:
        """Get outstanding amount."""
        if self.paid_amount:
            return float(self.payment_amount - self.paid_amount)
        return float(self.payment_amount)


class BidFollowUp(Base):
    """Follow-up tracking for bids and payments."""
    __tablename__ = "bid_follow_ups"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    bid_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_id: Mapped[UUID | None] = mapped_column(SQLAlchemyUUID, ForeignKey("bid_payments.id", ondelete="CASCADE"), nullable=True)

    # Follow-up details
    follow_up_type: Mapped[str] = mapped_column(String(50), nullable=False)  # payment, status, document, general
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")  # low, medium, high, urgent

    # Contact information
    contact_person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_method: Mapped[str] = mapped_column(String(50), nullable=False)  # email, phone, whatsapp, meeting

    # Status and scheduling
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")  # pending, completed, cancelled
    scheduled_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    bid: Mapped[Bid] = relationship("Bid", back_populates="follow_ups")
    payment: Mapped[BidPayment | None] = relationship("BidPayment")

    def __repr__(self) -> str:
        return f"BidFollowUp(id={self.id}, bid_id={self.bid_id}, type={self.follow_up_type})"

    @property
    def is_overdue(self) -> bool:
        """Check if follow-up is overdue."""
        if self.status == "completed":
            return False
        return datetime.utcnow() > self.scheduled_date

    @property
    def days_overdue(self) -> int:
        """Get days overdue."""
        if not self.is_overdue:
            return 0
        delta = datetime.utcnow() - self.scheduled_date
        return delta.days
