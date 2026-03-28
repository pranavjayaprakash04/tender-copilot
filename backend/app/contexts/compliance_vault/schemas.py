from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentTypeSchema(StrEnum):
    GST = "gst"
    PAN = "pan"
    ISO = "iso"
    UDYAM = "udyam"
    TRADE_LICENSE = "trade_license"
    BANK_GUARANTEE = "bank_guarantee"
    EXPERIENCE_CERTIFICATE = "experience_certificate"
    FINANCIAL_STATEMENT = "financial_statement"
    TAX_CLEARANCE = "tax_clearance"
    EMOLUMENT_CERTIFICATE = "emolument_certificate"
    OTHER = "other"


# Base schemas
class VaultDocumentBase(BaseModel):
    """Base vault document schema."""
    doc_type: DocumentTypeSchema
    filename: str = Field(..., min_length=1, max_length=255)
    expires_at: datetime | None = None


class VaultDocumentCreate(VaultDocumentBase):
    """Schema for creating a vault document."""
    company_id: UUID


class VaultDocumentUpdate(BaseModel):
    """Schema for updating a vault document."""
    filename: str | None = Field(None, min_length=1, max_length=255)
    expires_at: datetime | None = None
    is_current: bool | None = None
    storage_path: str | None = None  # ← needed for service to update final path after upload


# Response schemas
class VaultDocumentResponse(VaultDocumentBase):
    """Vault document response schema."""
    id: UUID
    company_id: UUID
    storage_path: str
    version: int
    is_current: bool
    uploaded_at: datetime

    # Computed properties
    is_expired: bool
    days_until_expiry: int | None
    is_expiring_soon: bool

    # Optional — only present on get_document (single fetch), not list
    download_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    """Document upload response schema."""
    document: VaultDocumentResponse
    upload_url: str | None = None  # For direct upload to storage


class DocumentListResponse(BaseModel):
    """Document list response schema."""
    documents: list[VaultDocumentResponse]
    total: int
    expiring_soon: list[VaultDocumentResponse]
    expired: list[VaultDocumentResponse]


# Tender mapping schemas
class TenderDocumentMappingCreate(BaseModel):
    """Schema for creating tender-document mapping."""
    tender_id: UUID
    document_ids: list[UUID]


class TenderDocumentMappingResponse(BaseModel):
    """Tender document mapping response schema."""
    tender_id: UUID
    documents: list[VaultDocumentResponse]

    model_config = ConfigDict(from_attributes=True)


# Document classification schemas
class DocumentClassificationRequest(BaseModel):
    """Request for document classification."""
    filename: str
    content_preview: str | None = None  # First few lines of document content


class DocumentClassificationResponse(BaseModel):
    """Document classification response."""
    doc_type: DocumentTypeSchema
    confidence: float = Field(..., ge=0.0, le=1.0)
    suggested_expiry: datetime | None = None
    reasoning: str


# Batch operations
class BatchDocumentUpdate(BaseModel):
    """Batch update schema for documents."""
    document_ids: list[UUID]
    updates: VaultDocumentUpdate


class BatchDocumentResponse(BaseModel):
    """Batch operation response."""
    updated: list[VaultDocumentResponse]
    failed: list[dict]  # {document_id: error_message}


# Search and filtering
class DocumentSearchFilters(BaseModel):
    """Document search filters."""
    doc_types: list[DocumentTypeSchema] | None = None
    is_current: bool | None = None
    is_expired: bool | None = None
    is_expiring_soon: bool | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None

    @field_validator('date_to')
    @classmethod
    def validate_date_range(cls, v, info):
        if v and info.data.get('date_from'):
            if v < info.data['date_from']:
                raise ValueError('date_to must be after date_from')
        return v


class DocumentStatsResponse(BaseModel):
    """Document statistics response."""
    total_documents: int
    current_documents: int
    expired_documents: int
    expiring_soon_documents: int
    by_type: dict[DocumentTypeSchema, int]
    upcoming_expiries: list[VaultDocumentResponse]  # Next 30 days
