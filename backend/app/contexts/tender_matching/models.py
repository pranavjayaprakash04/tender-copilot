from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    desc,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MatchStatus(StrEnum):
    """Tender matching status."""
    PENDING = "pending"
    MATCHING = "matching"
    COMPLETED = "completed"
    FAILED = "failed"


class TenderMatch(Base):
    """Tender-company matching model."""
    __tablename__ = "tender_matches"

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(PG_UUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    # tender_id stored as BigInteger — tenders table uses bigint PK (scraper-created)
    tender_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Matching results
    match_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=True)
    match_reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    gap_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Embedding data stored as JSON (pgvector not available)
    company_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tender_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(50), nullable=False, default="tfidf-v1")
    embedding_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    # Processing metadata
    status: Mapped[MatchStatus] = mapped_column(String(20), nullable=False, default=MatchStatus.PENDING)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    # Matching criteria
    industry_match: Mapped[float] = mapped_column(Float, nullable=True)
    size_match: Mapped[float] = mapped_column(Float, nullable=True)
    location_match: Mapped[float] = mapped_column(Float, nullable=True)
    value_match: Mapped[float] = mapped_column(Float, nullable=True)
    experience_match: Mapped[float] = mapped_column(Float, nullable=True)

    # Quality indicators
    completeness_score: Mapped[float] = mapped_column(Float, nullable=True)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=True)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=True)

    # User interaction
    is_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_shortlisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shortlisted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_rating: Mapped[int] = mapped_column(Integer, nullable=True)
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    company: Mapped[Any] = relationship("Company", back_populates="tender_matches")

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
        return self.match_score >= 0.8 and self.confidence_level == "high"

    @property
    def processing_duration(self) -> float | None:
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None

    @property
    def age_hours(self) -> float:
        return (datetime.utcnow() - self.created_at).total_seconds() / 3600


class CompanyEmbedding(Base):
    """Company capability embeddings."""
    __tablename__ = "company_embeddings"

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(PG_UUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    capabilities_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(50), nullable=False, default="tfidf-v1")
    embedding_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    capabilities_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    text_length: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=True)

    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    company: Mapped[Any] = relationship("Company", back_populates="embedding")

    def __repr__(self) -> str:
        return f"CompanyEmbedding(company_id={self.company_id}, model={self.embedding_model})"


class TenderEmbedding(Base):
    """Tender requirement embeddings."""
    __tablename__ = "tender_embeddings"

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=func.uuid_generate_v4())
    # tender_id stored as BigInteger — tenders table uses bigint PK
    tender_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)

    requirements_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(50), nullable=False, default="tfidf-v1")
    embedding_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    requirements_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    text_length: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=True)

    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"TenderEmbedding(tender_id={self.tender_id}, model={self.embedding_model})"


class MatchingAnalytics(Base):
    """Analytics for tender matching performance."""
    __tablename__ = "matching_analytics"

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(PG_UUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)

    total_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_quality_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_match_score: Mapped[float] = mapped_column(Float, nullable=True)
    average_processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shortlists_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversion_rate: Mapped[float] = mapped_column(Float, nullable=True)

    average_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"MatchingAnalytics(company_id={self.company_id}, period={self.period_type})"

    @property
    def high_quality_rate(self) -> float:
        if self.total_matches == 0:
            return 0.0
        return self.high_quality_matches / self.total_matches
