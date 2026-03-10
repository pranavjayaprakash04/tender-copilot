from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    desc,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


class MatchStatus(StrEnum):
    """Tender matching status."""
    PENDING = "pending"
    MATCHING = "matching"
    COMPLETED = "completed"
    FAILED = "failed"


class TenderMatch(Base):
    """Tender-company matching model with pgvector embeddings."""
    __tablename__ = "tender_matches"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tender_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)

    # Matching results
    match_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)  # 0.0-1.0 cosine similarity
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=True)  # high, medium, low
    match_reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # Reasons for match
    gap_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Capability gaps
    recommendations: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # Recommendations

    # Embedding data
    company_embedding: Mapped[Vector] = mapped_column(Vector(384), nullable=False)  # Company capability embedding
    tender_embedding: Mapped[Vector] = mapped_column(Vector(384), nullable=False)  # Tender requirement embedding
    embedding_model: Mapped[str] = mapped_column(String(50), nullable=False, default="all-MiniLM-L6-v2")
    embedding_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    # Processing metadata
    status: Mapped[MatchStatus] = mapped_column(String(20), nullable=False, default=MatchStatus.PENDING)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    # Matching criteria
    industry_match: Mapped[float] = mapped_column(Float, nullable=True)  # Industry compatibility score
    size_match: Mapped[float] = mapped_column(Float, nullable=True)  # Company size compatibility
    location_match: Mapped[float] = mapped_column(Float, nullable=True)  # Geographic compatibility
    value_match: Mapped[float] = mapped_column(Float, nullable=True)  # Tender value compatibility
    experience_match: Mapped[float] = mapped_column(Float, nullable=True)  # Past experience score

    # Quality indicators
    completeness_score: Mapped[float] = mapped_column(Float, nullable=True)  # Data completeness (0-1)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=True)  # How recent the data is (0-1)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=True)  # Data accuracy confidence (0-1)

    # User interaction
    is_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_shortlisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shortlisted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_rating: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-5 stars
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    company: Mapped[Any] = relationship("Company", back_populates="tender_matches")
    tender: Mapped[Any] = relationship("Tender", back_populates="company_matches")

    # Indexes for performance
    __table_args__ = (
        Index('idx_company_tender_match', 'company_id', 'tender_id'),
        Index('idx_match_score_desc', desc('match_score')),
        Index('idx_company_score', 'company_id', desc('match_score')),
        Index('idx_tender_score', 'tender_id', desc('match_score')),
        Index('idx_status_created', 'status', desc('created_at')),
    )

    def __repr__(self) -> str:
        return f"TenderMatch(id={self.id}, score={self.match_score:.3f}, status={self.status})"

    @property
    def is_high_match(self) -> bool:
        """Check if this is a high-quality match."""
        return self.match_score >= 0.8 and self.confidence_level == "high"

    @property
    def processing_duration(self) -> float | None:
        """Get processing duration in seconds."""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None

    @property
    def age_hours(self) -> float:
        """Get age of match in hours."""
        return (datetime.utcnow() - self.created_at).total_seconds() / 3600


class CompanyEmbedding(Base):
    """Company capability embeddings for faster matching."""
    __tablename__ = "company_embeddings"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Embedding data
    capabilities_embedding: Mapped[Vector] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(50), nullable=False, default="all-MiniLM-L6-v2")
    embedding_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    # Source data
    capabilities_text: Mapped[str] = mapped_column(Text, nullable=False)  # Original text used for embedding
    source_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Which fields contributed

    # Quality metrics
    text_length: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1

    # Processing metadata
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    company: Mapped[Any] = relationship("Company", back_populates="embedding")

    def __repr__(self) -> str:
        return f"CompanyEmbedding(company_id={self.company_id}, model={self.embedding_model})"


class TenderEmbedding(Base):
    """Tender requirement embeddings for faster matching."""
    __tablename__ = "tender_embeddings"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=func.uuid_generate_v4())
    tender_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Embedding data
    requirements_embedding: Mapped[Vector] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(50), nullable=False, default="all-MiniLM-L6-v2")
    embedding_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    # Source data
    requirements_text: Mapped[str] = mapped_column(Text, nullable=False)  # Original text used for embedding
    source_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Which fields contributed

    # Quality metrics
    text_length: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1

    # Processing metadata
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    tender: Mapped[Any] = relationship("Tender", back_populates="embedding")

    def __repr__(self) -> str:
        return f"TenderEmbedding(tender_id={self.tender_id}, model={self.embedding_model})"


class MatchingAnalytics(Base):
    """Analytics for tender matching performance."""
    __tablename__ = "matching_analytics"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Analytics period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, weekly, monthly

    # Matching metrics
    total_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_quality_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # score >= 0.8
    average_match_score: Mapped[float] = mapped_column(Float, nullable=True)
    average_processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    # Engagement metrics
    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shortlists_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversion_rate: Mapped[float] = mapped_column(Float, nullable=True)  # shortlists/views

    # Quality metrics
    average_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=True)  # Based on user feedback

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"MatchingAnalytics(company_id={self.company_id}, period={self.period_type})"

    @property
    def high_quality_rate(self) -> float:
        """Calculate high-quality match rate."""
        if self.total_matches == 0:
            return 0.0
        return self.high_quality_matches / self.total_matches
