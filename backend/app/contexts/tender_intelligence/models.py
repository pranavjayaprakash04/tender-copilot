from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import UUID as SQLAlchemyUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class DocumentType(StrEnum):
    """Document types for tender intelligence."""
    TENDER_NOTICE = "tender_notice"
    BID_DOCUMENT = "bid_document"
    TECHNICAL_SPECIFICATION = "technical_specification"
    ELIGIBILITY_CRITERIA = "eligibility_criteria"
    FINANCIAL_BID = "financial_bid"
    CORRIGENDUM = "corrigendum"
    ADDENDUM = "addendum"
    OTHER = "other"


class ProcessingStatus(StrEnum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class TenderDocument(Base):
    """Tender document model for AI processing."""
    __tablename__ = "tender_documents"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tender_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)

    # Document details
    document_type: Mapped[DocumentType] = mapped_column(String(50), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Processing status and metadata
    processing_status: Mapped[ProcessingStatus] = mapped_column(String(20), nullable=False, default=ProcessingStatus.PENDING)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Extracted content
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_length: Mapped[int] = mapped_column(Integer, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    language_detected: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # AI analysis results
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_key_requirements: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_eligibility_criteria: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_evaluation_criteria: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_risk_factors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_recommendations: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_confidence_score: Mapped[float | None] = mapped_column(Integer, nullable=True)  # 0-100
    ai_processing_time: Mapped[float | None] = mapped_column(Integer, nullable=True)  # milliseconds

    # Document metadata
    document_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    is_confidential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    access_level: Mapped[str] = mapped_column(String(20), nullable=False, default="internal")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"TenderDocument(id={self.id}, type={self.document_type}, status={self.processing_status})"

    @property
    def can_retry(self) -> bool:
        """Check if document processing can be retried."""
        return self.retry_count < self.max_retries and self.processing_status == ProcessingStatus.FAILED

    @property
    def is_processed(self) -> bool:
        """Check if document has been processed successfully."""
        return self.processing_status == ProcessingStatus.COMPLETED

    @property
    def processing_duration(self) -> float | None:
        """Get processing duration in seconds."""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None


class DocumentChunk(Base):
    """Document chunks for embedding and search."""
    __tablename__ = "document_chunks"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    document_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("tender_documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Chunk content
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")  # text, table, image_caption
    page_number: Mapped[int] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Embedding data
    embedding_vector: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)  # For vector search
    embedding_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Search and classification
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    importance_score: Mapped[float] = mapped_column(Integer, nullable=False, default=0.0)  # 0-1
    is_requirement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_deadline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_financial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"DocumentChunk(id={self.id}, doc_id={self.document_id}, page={self.page_number})"


class TenderIntelligenceReport(Base):
    """AI-generated intelligence reports for tenders."""
    __tablename__ = "tender_intelligence_reports"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tender_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)

    # Report details
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # summary, analysis, recommendation
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    report_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")

    # AI processing info
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Integer, nullable=False)  # 0-100

    # Report content
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_findings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    risk_assessment: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    recommendations: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    next_steps: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Source documents
    source_document_ids: Mapped[list[UUID]] = mapped_column(JSON, nullable=False)
    total_documents_analyzed: Mapped[int] = mapped_column(Integer, nullable=False)
    total_pages_processed: Mapped[int] = mapped_column(Integer, nullable=False)

    # Quality metrics
    completeness_score: Mapped[float] = mapped_column(Integer, nullable=False)  # 0-100
    accuracy_score: Mapped[float] = mapped_column(Integer, nullable=False)  # 0-100
    relevance_score: Mapped[float] = mapped_column(Integer, nullable=False)  # 0-100

    # User feedback
    user_rating: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-5 stars
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_helpful: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"TenderIntelligenceReport(id={self.id}, tender_id={self.tender_id}, type={self.report_type})"

    @property
    def average_quality_score(self) -> float:
        """Calculate average quality score."""
        return (self.completeness_score + self.accuracy_score + self.relevance_score) / 3
