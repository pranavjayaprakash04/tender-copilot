from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
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

from app.database import Base


class BidStatus(StrEnum):
    DRAFT = "draft"
    REVIEWING = "reviewing"
    SUBMITTED = "submitted"
    UNDER_EVALUATION = "under_evaluation"
    WON = "won"
    LOST = "lost"
    WITHDRAWN = "withdrawn"
    DISQUALIFIED = "disqualified"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class BidOutcome(StrEnum):
    WON = "won"
    LOST = "lost"
    WITHDRAWN = "withdrawn"
    DISQUALIFIED = "disqualified"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    FULLY_PAID = "fully_paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"
    WRITTEN_OFF = "written_off"


class Bid(Base):
    """Bid lifecycle model."""

    __tablename__ = "bids"

    # Status transition map
    _TRANSITIONS: dict[BidStatus, set[BidStatus]] = {
        BidStatus.DRAFT: {BidStatus.REVIEWING, BidStatus.CANCELLED, BidStatus.WITHDRAWN},
        BidStatus.REVIEWING: {BidStatus.SUBMITTED, BidStatus.DRAFT, BidStatus.ON_HOLD, BidStatus.CANCELLED},
        BidStatus.SUBMITTED: {BidStatus.UNDER_EVALUATION, BidStatus.WITHDRAWN},
        BidStatus.UNDER_EVALUATION: {BidStatus.WON, BidStatus.LOST, BidStatus.DISQUALIFIED},
        BidStatus.ON_HOLD: {BidStatus.REVIEWING, BidStatus.CANCELLED, BidStatus.WITHDRAWN},
        BidStatus.WON: set(),
        BidStatus.LOST: set(),
        BidStatus.WITHDRAWN: set(),
        BidStatus.DISQUALIFIED: set(),
        BidStatus.CANCELLED: set(),
    }

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default="gen_random_uuid()")
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, nullable=False, index=True)
    tender_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)
    bid_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Financial
    bid_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    emd_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    bid_security_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    # Dates
    submission_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    award_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    status: Mapped[BidStatus] = mapped_column(String(30), nullable=False, default=BidStatus.DRAFT)
    previous_status: Mapped[BidStatus | None] = mapped_column(String(30), nullable=True)

    # Team
    lead_bidder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bid_manager: Mapped[str | None] = mapped_column(String(255), nullable=True)
    technical_lead: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Scores
    compliance_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    financial_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow)

    # ── Helper methods ──────────────────────────────────────────────

    def can_transition_to(self, new_status: BidStatus) -> bool:
        """Check if transitioning to new_status is allowed from current status."""
        return new_status in self._TRANSITIONS.get(self.status, set())

    def get_allowed_transitions(self) -> list[BidStatus]:
        """Return list of valid next statuses from current status."""
        return list(self._TRANSITIONS.get(self.status, set()))

    @property
    def can_edit(self) -> bool:
        return self.status in {BidStatus.DRAFT, BidStatus.REVIEWING, BidStatus.ON_HOLD}

    @property
    def can_submit(self) -> bool:
        return self.status == BidStatus.REVIEWING

    @property
    def can_withdraw(self) -> bool:
        return self.status in {BidStatus.DRAFT, BidStatus.REVIEWING, BidStatus.SUBMITTED}

    @property
    def is_final_status(self) -> bool:
        return self.status in {
            BidStatus.WON,
            BidStatus.LOST,
            BidStatus.WITHDRAWN,
            BidStatus.DISQUALIFIED,
            BidStatus.CANCELLED,
        }

    @property
    def days_since_submission(self) -> int | None:
        if self.submission_date:
            return (datetime.utcnow() - self.submission_date.replace(tzinfo=None)).days
        return None

    @property
    def is_overdue_payment(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"Bid(id={self.id}, number={self.bid_number}, status={self.status})"


class BidOutcomeRecord(Base):
    """Record of bid outcome details."""

    __tablename__ = "bid_outcomes"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default="gen_random_uuid()")
    bid_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, nullable=False, index=True)
    outcome: Mapped[BidOutcome] = mapped_column(String(30), nullable=False)

    # Loss details
    loss_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loss_reason_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    winning_bidder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    winning_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    competitor_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    our_ranking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow)


class BidPayment(Base):
    """Payment tracking for won bids."""

    __tablename__ = "bid_payments"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default="gen_random_uuid()")
    bid_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, nullable=False, index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(String(30), nullable=False, default=PaymentStatus.PENDING)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow)

    @property
    def is_overdue(self) -> bool:
        if self.due_date and self.status not in {PaymentStatus.FULLY_PAID, PaymentStatus.WRITTEN_OFF}:
            return datetime.utcnow() > self.due_date.replace(tzinfo=None)
        return False

    @property
    def days_overdue(self) -> int:
        if self.is_overdue and self.due_date:
            return (datetime.utcnow() - self.due_date.replace(tzinfo=None)).days
        return 0


class BidFollowUp(Base):
    """Follow-up tasks for bids and payments."""

    __tablename__ = "bid_follow_ups"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, server_default="gen_random_uuid()")
    bid_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_id: Mapped[UUID | None] = mapped_column(SQLAlchemyUUID, nullable=True)
    company_id: Mapped[UUID | None] = mapped_column(SQLAlchemyUUID, nullable=True)
    follow_up_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    contact_method: Mapped[str] = mapped_column(String(50), nullable=False, default="email")
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow)
