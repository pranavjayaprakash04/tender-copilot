from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import UUID as SQLAlchemyUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class BidStatus(StrEnum):
    """Bid generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BidType(StrEnum):
    """Bid types."""
    TECHNICAL = "technical"
    FINANCIAL = "financial"
    COMBINED = "combined"
    QUALIFICATION = "qualification"


class BidGeneration(Base):
    """Bid generation model for tracking AI-powered bid creation."""
    __tablename__ = "bid_generations"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tender_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

    # Bid details
    bid_type: Mapped[BidType] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    bid_title: Mapped[str] = mapped_column(String(500), nullable=False)
    bid_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generation status and metadata
    status: Mapped[BidStatus] = mapped_column(String(20), nullable=False, default=BidStatus.PENDING)
    generation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # AI processing info
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False, default="llama-3.3-70b-versatile")
    ai_prompt_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1

    # Generated content
    bid_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_proposal: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    financial_proposal: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    compliance_matrix: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    risk_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    implementation_plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Quality metrics
    completeness_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1
    compliance_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1
    competitiveness_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1
    overall_quality_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1

    # User feedback
    user_rating: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-5 stars
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(SQLAlchemyUUID, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    generation_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    template_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customization_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"BidGeneration(id={self.id}, task_id={self.task_id}, status={self.status})"

    @property
    def can_retry(self) -> bool:
        """Check if bid generation can be retried."""
        return self.retry_count < self.max_retries and self.status == BidStatus.FAILED

    @property
    def is_completed(self) -> bool:
        """Check if bid generation is completed."""
        return self.status == BidStatus.COMPLETED

    @property
    def generation_duration(self) -> float | None:
        """Get generation duration in seconds."""
        if self.generation_started_at and self.generation_completed_at:
            return (self.generation_completed_at - self.generation_started_at).total_seconds()
        return None

    @property
    def estimated_completion_time(self) -> datetime | None:
        """Get estimated completion time based on bid type."""
        if self.status != BidStatus.PENDING:
            return None

        # Base estimation times in minutes
        base_times = {
            BidType.TECHNICAL: 15,
            BidType.FINANCIAL: 10,
            BidType.COMBINED: 25,
            BidType.QUALIFICATION: 8
        }

        base_time = base_times.get(self.bid_type, 15)
        return self.created_at + timedelta(minutes=base_time)


class BidTemplate(Base):
    """Bid templates for different tender types."""
    __tablename__ = "bid_templates"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Template details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_type: Mapped[BidType] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    # Template content
    template_structure: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    sections: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    placeholders: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1
    average_rating: Mapped[float] = mapped_column(Float, nullable=True)  # 0-5

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"BidTemplate(id={self.id}, name={self.name}, type={self.template_type})"


class BidGenerationAnalytics(Base):
    """Analytics for bid generation performance."""
    __tablename__ = "bid_generation_analytics"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Analytics period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, weekly, monthly

    # Generation metrics
    total_generations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_generations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_generations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    # Quality metrics
    average_quality_score: Mapped[float] = mapped_column(Float, nullable=True)
    average_confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    user_satisfaction_rate: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1

    # Type breakdown
    generations_by_type: Mapped[dict[str, int]] = mapped_column(JSON, nullable=True)
    success_rate_by_type: Mapped[dict[str, float]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"BidGenerationAnalytics(id={self.id}, period={self.period_type}, success_rate={self.success_rate})"

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_generations == 0:
            return 0.0
        return self.successful_generations / self.total_generations
