from __future__ import annotations

from datetime import datetime, timedelta, UTC
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class DocumentType(StrEnum):
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


class VaultDocument(Base):
    """Compliance vault document model."""
    __tablename__ = "vault_documents"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    doc_type: Mapped[DocumentType] = mapped_column(String(50), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Fixed: added company relationship that was missing (caused crash in get_by_tender)
    company: Mapped["Company"] = relationship("Company", back_populates="vault_documents", lazy="select")  # type: ignore[name-defined]

    # Relationships
    tender_mappings: Mapped[list[VaultDocumentMapping]] = relationship(
        "VaultDocumentMapping",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"VaultDocument(id={self.id}, company_id={self.company_id}, doc_type={self.doc_type})"

    @property
    def is_expired(self) -> bool:
        """Check if document is expired."""
        if not self.expires_at:
            return False
        # Fixed: use timezone-aware datetime
        return datetime.now(UTC) > self.expires_at

    @property
    def days_until_expiry(self) -> int | None:
        """Get days until expiry."""
        if not self.expires_at:
            return None
        # Fixed: use timezone-aware datetime
        delta = self.expires_at - datetime.now(UTC)
        return delta.days if delta.days > 0 else 0

    @property
    def is_expiring_soon(self) -> bool:
        """Check if document is expiring within 30 days."""
        # Fixed: removed `days` parameter from property (Python properties can't have params)
        if not self.expires_at:
            return False
        expiry_threshold = datetime.now(UTC) + timedelta(days=30)
        return self.expires_at <= expiry_threshold


class VaultDocumentMapping(Base):
    """Mapping between vault documents and tenders."""
    __tablename__ = "vault_document_mappings"

    vault_doc_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("vault_documents.id", ondelete="CASCADE"),
        primary_key=True
    )
    tender_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        primary_key=True
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    document: Mapped[VaultDocument] = relationship("VaultDocument", back_populates="tender_mappings")

    def __repr__(self) -> str:
        return f"VaultDocumentMapping(vault_doc_id={self.vault_doc_id}, tender_id={self.tender_id})"
