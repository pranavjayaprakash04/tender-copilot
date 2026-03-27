from __future__ import annotations

import os
import re
from datetime import datetime, UTC
from uuid import UUID

import structlog
from fastapi import UploadFile

from app.contexts.compliance_vault.models import DocumentType
from app.contexts.compliance_vault.repository import (
    VaultDocumentMappingRepository,
    VaultDocumentRepository,
)
from app.contexts.compliance_vault.schemas import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    DocumentListResponse,
    DocumentSearchFilters,
    DocumentStatsResponse,
    TenderDocumentMappingCreate,
    TenderDocumentMappingResponse,
    VaultDocumentCreate,
    VaultDocumentResponse,
    VaultDocumentUpdate,
)
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.infrastructure.storage import StorageClient
from app.prompts.compliance.document_match_v1 import SYSTEM_PROMPT, build_prompt
from app.shared.exceptions import (
    FileUploadException,
    ValidationException,
)
from app.shared.lang_context import LangContext

logger = structlog.get_logger()

_PDF_MAGIC = b"%PDF"

# Dangerous PDF stream keywords that indicate active content
_DANGEROUS_PDF_PATTERNS = [
    b"/JS",
    b"/JavaScript",
    b"/AA",           # Auto Action
    b"/OpenAction",   # Runs on open
    b"/Launch",       # Launches external app
    b"/EmbeddedFile", # Embedded file streams
    b"/RichMedia",    # Flash/video embeds
    b"/XFA",          # XML Forms Architecture (can run scripts)
]

# Windows PE header — catches executables disguised as PDFs
_PE_MAGIC = b"MZ"

# Max filename length to prevent DoS via long filenames
_MAX_FILENAME_LEN = 255

# Allowed filename characters (alphanumeric, spaces, hyphens, underscores, dots)
_SAFE_FILENAME_RE = re.compile(r"^[\w\s\-. ()]+$")


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and injection attacks.
    - Strips directory components (path traversal)
    - Removes null bytes
    - Limits length
    - Allows only safe characters
    """
    # Strip any directory components (path traversal)
    filename = os.path.basename(filename)

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Limit length
    if len(filename) > _MAX_FILENAME_LEN:
        name, ext = os.path.splitext(filename)
        filename = name[:_MAX_FILENAME_LEN - len(ext)] + ext

    # Enforce safe character set
    if not _SAFE_FILENAME_RE.match(filename):
        raise ValidationException(
            "Filename contains invalid characters. Use only letters, numbers, spaces, hyphens, underscores, and dots."
        )

    return filename


def _validate_pdf_content(file_content: bytes) -> None:
    """
    Deep validation of PDF bytes:
    1. Magic bytes check (must start with %PDF)
    2. PE header check (catches EXE disguised as PDF)
    3. Dangerous stream keyword scan (JS, auto-actions, embedded files)
    4. Ensures file ends with %%EOF (basic structure check)
    """
    # 1. Magic bytes — must start with %PDF
    if file_content[:4] != _PDF_MAGIC:
        raise ValidationException("File must be a valid PDF (invalid magic bytes)")

    # 2. PE header check anywhere in first 1KB — polyglot PDF/EXE detection
    if _PE_MAGIC in file_content[:1024]:
        raise ValidationException("File contains executable content and has been rejected")

    # 3. Scan entire file for dangerous PDF stream keywords
    for pattern in _DANGEROUS_PDF_PATTERNS:
        if pattern in file_content:
            keyword = pattern.decode("ascii", errors="replace")
            raise ValidationException(
                f"PDF contains disallowed active content ({keyword}) and has been rejected"
            )

    # 4. Basic structural check — valid PDFs end with %%EOF
    # Check last 1024 bytes to allow for trailing whitespace/comments
    tail = file_content[-1024:]
    if b"%%EOF" not in tail:
        raise ValidationException("File does not appear to be a valid PDF (missing %%EOF marker)")


class ComplianceVaultService:
    """Service for compliance vault operations."""

    def __init__(
        self,
        document_repo: VaultDocumentRepository,
        mapping_repo: VaultDocumentMappingRepository,
        storage_client: StorageClient,
        groq_client: GroqClient,
    ) -> None:
        self._document_repo = document_repo
        self._mapping_repo = mapping_repo
        self._storage = storage_client
        self._groq = groq_client

    async def upload_document(
        self,
        file: UploadFile,
        doc_type: DocumentType,
        company_id: UUID,
        expires_at: datetime | None = None,
        lang: LangContext = LangContext.from_lang("en"),
        trace_id: str | None = None
    ) -> VaultDocumentResponse:
        """Upload a document to the vault."""

        # ── Filename validation ────────────────────────────────────────────────
        if not file.filename:
            raise ValidationException("Filename is required")

        if not file.filename.lower().endswith(".pdf"):
            raise ValidationException("Only PDF files are supported")

        # Sanitize filename — prevents path traversal and injection
        safe_filename = _sanitize_filename(file.filename)

        # ── Read file into memory ──────────────────────────────────────────────
        file_content = await file.read()

        # ── Size check on real bytes (not spoofable Content-Length header) ─────
        if len(file_content) == 0:
            raise ValidationException("File is empty")

        if len(file_content) > 10 * 1024 * 1024:
            raise FileUploadException("File size exceeds 10MB limit")

        # ── Deep PDF content validation ────────────────────────────────────────
        # This is the main security gate: magic bytes, PE header, dangerous
        # stream keywords, and structural EOF check all happen here.
        try:
            _validate_pdf_content(file_content)
        except ValidationException:
            logger.warning(
                "pdf_validation_rejected",
                trace_id=trace_id,
                filename=safe_filename,
                company_id=str(company_id),
            )
            raise

        document_data = VaultDocumentCreate(
            company_id=company_id,
            doc_type=doc_type,
            filename=safe_filename,
            expires_at=expires_at
        )

        # ── Step 1: Upload to storage first ───────────────────────────────────
        # DB record is only created after storage succeeds (atomic ordering)
        temp_path = f"companies/{company_id}/documents/temp_{safe_filename}"
        try:
            await self._storage.upload_file(temp_path, file_content, "application/pdf")
        except Exception as e:
            logger.error("storage_upload_failed", trace_id=trace_id, error=str(e))
            raise FileUploadException(f"Failed to upload document: {e}")

        # ── Step 2: Create DB record ───────────────────────────────────────────
        try:
            document = await self._document_repo.create(document_data)
        except Exception as e:
            # Storage uploaded but DB failed — clean up storage to avoid orphans
            try:
                await self._storage.delete_file(temp_path)
            except Exception:
                pass
            logger.error("db_create_failed_after_upload", trace_id=trace_id, error=str(e))
            raise FileUploadException(f"Failed to save document record: {e}")

        # ── Step 3: Move to final path with real document ID ──────────────────
        final_path = f"companies/{company_id}/documents/{document.id}/{safe_filename}"
        try:
            await self._storage.upload_file(final_path, file_content, "application/pdf")
            await self._storage.delete_file(temp_path)
        except Exception as e:
            logger.warning("final_path_move_failed", trace_id=trace_id, error=str(e))
            final_path = temp_path

        # ── Step 4: Update document with final storage path ───────────────────
        document.storage_path = final_path
        await self._document_repo.update(
            document.id, company_id,
            VaultDocumentUpdate(storage_path=final_path)
        )

        logger.info(
            "document_uploaded",
            trace_id=trace_id,
            document_id=document.id,
            company_id=company_id,
            doc_type=doc_type,
            filename=safe_filename,
        )

        return VaultDocumentResponse.model_validate(document)

    async def get_document(
        self,
        document_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> VaultDocumentResponse:
        """Get a document by ID."""
        document = await self._document_repo.get_by_id(document_id, company_id)

        download_url = await self._storage.get_download_url(document.storage_path)

        response = VaultDocumentResponse.model_validate(document)
        response.download_url = download_url  # type: ignore

        logger.info("document_retrieved", trace_id=trace_id, document_id=document_id, company_id=company_id)

        return response

    async def list_documents(
        self,
        company_id: UUID,
        filters: DocumentSearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
        trace_id: str | None = None
    ) -> tuple[DocumentListResponse, int]:
        """List documents for a company."""
        documents, total = await self._document_repo.get_by_company(
            company_id, filters, page, page_size
        )

        expiring_soon = await self._document_repo.get_expiring_soon(company_id)
        expired = await self._document_repo.get_expired(company_id)

        logger.info("documents_listed", trace_id=trace_id, company_id=company_id, total=total)

        return DocumentListResponse(
            documents=[VaultDocumentResponse.model_validate(doc) for doc in documents],
            total=total,
            expiring_soon=[VaultDocumentResponse.model_validate(doc) for doc in expiring_soon],
            expired=[VaultDocumentResponse.model_validate(doc) for doc in expired]
        ), total

    async def update_document(
        self,
        document_id: UUID,
        company_id: UUID,
        update_data: VaultDocumentUpdate,
        trace_id: str | None = None
    ) -> VaultDocumentResponse:
        """Update a document."""
        document = await self._document_repo.update(document_id, company_id, update_data)
        logger.info("document_updated", trace_id=trace_id, document_id=document_id, company_id=company_id)
        return VaultDocumentResponse.model_validate(document)

    async def delete_document(
        self,
        document_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> None:
        """Delete a document."""
        document = await self._document_repo.get_by_id(document_id, company_id)

        try:
            await self._storage.delete_file(document.storage_path)
        except Exception as e:
            logger.warning(
                "storage_delete_failed",
                trace_id=trace_id,
                document_id=document_id,
                error=str(e)
            )

        await self._document_repo.delete(document_id, company_id)
        logger.info("document_deleted", trace_id=trace_id, document_id=document_id, company_id=company_id)

    async def classify_document(
        self,
        request: DocumentClassificationRequest,
        lang: LangContext = LangContext.from_lang("en"),
        trace_id: str | None = None,
        company_id: str | None = None
    ) -> DocumentClassificationResponse:
        """Classify a document type using AI."""
        try:
            from app.prompts.compliance.document_classification_v1 import (
                ClassificationOutput,
                CLASSIFICATION_SYSTEM_PROMPT,
                build_classification_prompt,
            )

            user_prompt = build_classification_prompt(request.filename, request.content_preview or "")

            result = await self._groq.complete(
                model=GroqModel.FAST,
                system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                output_schema=ClassificationOutput,
                lang=lang,
                trace_id=trace_id,
                company_id=company_id,
                temperature=0.3
            )

            logger.info(
                "document_classified",
                trace_id=trace_id,
                filename=request.filename,
                doc_type=result.doc_type,
                confidence=result.confidence
            )

            return DocumentClassificationResponse(
                doc_type=result.doc_type,
                confidence=result.confidence,
                suggested_expiry=result.suggested_expiry,
                reasoning=result.reasoning
            )

        except Exception as e:
            logger.error("document_classification_failed", trace_id=trace_id, error=str(e))
            raise ValidationException(f"Failed to classify document: {e}")

    async def get_document_stats(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> DocumentStatsResponse:
        """Get document statistics for a company."""
        stats = await self._document_repo.get_stats(company_id)
        upcoming_expiries = await self._document_repo.get_expiring_soon(company_id, 30)

        logger.info("document_stats_retrieved", trace_id=trace_id, company_id=company_id)

        return DocumentStatsResponse(
            total_documents=stats["total_documents"],
            current_documents=stats["current_documents"],
            expired_documents=stats["expired_documents"],
            expiring_soon_documents=stats["expiring_soon_documents"],
            by_type=stats["by_type"],
            upcoming_expiries=[VaultDocumentResponse.model_validate(doc) for doc in upcoming_expiries]
        )

    async def map_documents_to_tender(
        self,
        mapping_data: TenderDocumentMappingCreate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> TenderDocumentMappingResponse:
        """Map documents to a tender — verifies all docs belong to company first."""
        documents = []
        for doc_id in mapping_data.document_ids:
            doc = await self._document_repo.get_by_id(doc_id, company_id)
            documents.append(doc)

        for doc_id in mapping_data.document_ids:
            await self._mapping_repo.create_mapping(mapping_data.tender_id, doc_id)

        logger.info(
            "documents_mapped_to_tender",
            trace_id=trace_id,
            tender_id=mapping_data.tender_id,
            company_id=company_id,
            document_count=len(mapping_data.document_ids)
        )

        return TenderDocumentMappingResponse(
            tender_id=mapping_data.tender_id,
            documents=[VaultDocumentResponse.model_validate(doc) for doc in documents]
        )

    async def get_tender_documents(
        self,
        tender_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> TenderDocumentMappingResponse:
        """Get all documents mapped to a tender — scoped to company."""
        documents = await self._mapping_repo.get_by_tender(tender_id, company_id)

        logger.info(
            "tender_documents_retrieved",
            trace_id=trace_id,
            tender_id=tender_id,
            company_id=company_id,
            document_count=len(documents)
        )

        return TenderDocumentMappingResponse(
            tender_id=tender_id,
            documents=[VaultDocumentResponse.model_validate(doc) for doc in documents]
        )

    async def get_required_documents_for_tender(
        self,
        tender_title: str,
        tender_requirements: str,
        company_id: UUID,
        lang: LangContext = LangContext.from_lang("en"),
        trace_id: str | None = None
    ) -> list[DocumentType]:
        """Get required document types for a tender using AI."""
        try:
            from app.prompts.compliance.document_match_v1 import (
                DocumentMatchOutput,
                SYSTEM_PROMPT as MATCH_SYSTEM_PROMPT,
                build_prompt as build_match_prompt,
            )

            user_prompt = build_match_prompt(tender_title, tender_requirements)

            result = await self._groq.complete(
                model=GroqModel.PRIMARY,
                system_prompt=MATCH_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                output_schema=DocumentMatchOutput,
                lang=lang,
                trace_id=trace_id,
                company_id=str(company_id),
                temperature=0.5
            )

            logger.info(
                "tender_document_requirements_analyzed",
                trace_id=trace_id,
                tender_title=tender_title,
                required_count=len(result.required_documents)
            )

            return result.required_documents

        except Exception as e:
            logger.error("tender_document_analysis_failed", trace_id=trace_id, error=str(e))
            raise ValidationException(f"Failed to analyze document requirements: {e}")
