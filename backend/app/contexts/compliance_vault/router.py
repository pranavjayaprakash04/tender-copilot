from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from app.contexts.compliance_vault.models import DocumentType
from app.contexts.compliance_vault.schemas import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    DocumentSearchFilters,
    DocumentStatsResponse,
    TenderDocumentMappingCreate,
    TenderDocumentMappingResponse,
    VaultDocumentResponse,
    VaultDocumentUpdate,
)
from app.contexts.compliance_vault.service import ComplianceVaultService
from app.dependencies import (
    get_current_company_id,
    get_current_user_id,
    get_db_session,
    get_lang_context,
    get_pagination_params,
    get_trace_id,
)
from app.shared.lang_context import LangContext
from app.shared.schemas import BaseResponse, PaginatedResponse

router = APIRouter(prefix="/vault", tags=["compliance-vault"])


def get_vault_service(
    session = Depends(get_db_session)
) -> ComplianceVaultService:
    """Dependency to get vault service."""
    from app.contexts.compliance_vault.repository import (
        VaultDocumentMappingRepository,
        VaultDocumentRepository,
    )
    from app.infrastructure.groq_client import GroqClient
    from app.infrastructure.storage import StorageClient

    return ComplianceVaultService(
        document_repo=VaultDocumentRepository(session),
        mapping_repo=VaultDocumentMappingRepository(session),
        storage_client=StorageClient(),
        groq_client=GroqClient()
    )


@router.post("/upload", response_model=BaseResponse[VaultDocumentResponse])
async def upload_document(
    file: UploadFile = File(...),
    doc_type: DocumentType = Query(...),
    expires_at: str | None = Query(None),
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    lang: LangContext = Depends(get_lang_context),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[VaultDocumentResponse]:
    """Upload a document to the compliance vault."""
    from datetime import datetime

    # Chrome (and some other browsers) mis-label PDF parts in multipart forms
    # as text/plain. Force the correct MIME type so Supabase Storage accepts it.
    file.content_type = "application/pdf"

    expiry_date = None
    if expires_at:
        try:
            expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiry date format")

    document = await service.upload_document(
        file=file,
        doc_type=doc_type,
        company_id=company_id,
        expires_at=expiry_date,
        lang=lang,
        trace_id=trace_id
    )

    return BaseResponse(data=document, trace_id=trace_id)


@router.get("/documents", response_model=PaginatedResponse[VaultDocumentResponse])
async def list_documents(
    doc_types: list[DocumentType] | None = Query(None),
    is_current: bool | None = Query(None),
    is_expired: bool | None = Query(None),
    is_expiring_soon: bool | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    pagination: dict = Depends(get_pagination_params),
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> PaginatedResponse[VaultDocumentResponse]:
    """List documents with optional filters."""
    from datetime import datetime

    filters = DocumentSearchFilters(
        doc_types=doc_types,
        is_current=is_current,
        is_expired=is_expired,
        is_expiring_soon=is_expiring_soon,
        date_from=datetime.fromisoformat(date_from.replace('Z', '+00:00')) if date_from else None,
        date_to=datetime.fromisoformat(date_to.replace('Z', '+00:00')) if date_to else None
    )

    documents, total = await service.list_documents(
        company_id=company_id,
        filters=filters,
        page=pagination["page"],
        page_size=pagination["page_size"],
        trace_id=trace_id
    )

    return PaginatedResponse(
        data=documents.documents,
        pagination={
            "page": pagination["page"],
            "page_size": pagination["page_size"],
            "total_items": total,
            "total_pages": (total + pagination["page_size"] - 1) // pagination["page_size"],
            "has_next": pagination["page"] * pagination["page_size"] < total,
            "has_previous": pagination["page"] > 1
        },
        trace_id=trace_id
    )


@router.get("/documents/{document_id}", response_model=BaseResponse[VaultDocumentResponse])
async def get_document(
    document_id: UUID,
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[VaultDocumentResponse]:
    """Get a specific document."""
    document = await service.get_document(document_id, company_id, trace_id)
    return BaseResponse(data=document, trace_id=trace_id)


@router.put("/documents/{document_id}", response_model=BaseResponse[VaultDocumentResponse])
async def update_document(
    document_id: UUID,
    update_data: VaultDocumentUpdate,
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[VaultDocumentResponse]:
    """Update a document."""
    document = await service.update_document(document_id, company_id, update_data, trace_id)
    return BaseResponse(data=document, trace_id=trace_id)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Delete a document."""
    await service.delete_document(document_id, company_id, trace_id)
    return JSONResponse(content={"message": "Document deleted successfully"}, status_code=200)


@router.post("/classify", response_model=BaseResponse[DocumentClassificationResponse])
async def classify_document(
    request: DocumentClassificationRequest,
    service: ComplianceVaultService = Depends(get_vault_service),
    lang: LangContext = Depends(get_lang_context),
    trace_id: str = Depends(get_trace_id),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id)
) -> BaseResponse[DocumentClassificationResponse]:
    """Classify a document type using AI."""
    classification = await service.classify_document(
        request=request,
        lang=lang,
        trace_id=trace_id,
        company_id=str(company_id)
    )
    return BaseResponse(data=classification, trace_id=trace_id)


@router.get("/stats", response_model=BaseResponse[DocumentStatsResponse])
async def get_document_stats(
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[DocumentStatsResponse]:
    """Get document statistics."""
    stats = await service.get_document_stats(company_id, trace_id)
    return BaseResponse(data=stats, trace_id=trace_id)


@router.post("/tenders/{tender_id}/map", response_model=BaseResponse[TenderDocumentMappingResponse])
async def map_documents_to_tender(
    tender_id: UUID,
    mapping_data: TenderDocumentMappingCreate,
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderDocumentMappingResponse]:
    """Map documents to a tender."""
    mapping_data.tender_id = tender_id
    mapping = await service.map_documents_to_tender(mapping_data, company_id, trace_id)
    return BaseResponse(data=mapping, trace_id=trace_id)


@router.get("/tenders/{tender_id}/documents", response_model=BaseResponse[TenderDocumentMappingResponse])
async def get_tender_documents(
    tender_id: UUID,
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderDocumentMappingResponse]:
    """Get all documents mapped to a tender."""
    documents = await service.get_tender_documents(tender_id, company_id, trace_id)
    return BaseResponse(data=documents, trace_id=trace_id)


@router.post("/tenders/analyze-requirements", response_model=BaseResponse[list[DocumentType]])
async def analyze_tender_requirements(
    tender_title: str = Query(...),
    tender_requirements: str = Query(...),
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    lang: LangContext = Depends(get_lang_context),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[DocumentType]]:
    """Analyze tender requirements and suggest required documents."""
    required_docs = await service.get_required_documents_for_tender(
        tender_title=tender_title,
        tender_requirements=tender_requirements,
        company_id=company_id,
        lang=lang,
        trace_id=trace_id
    )
    return BaseResponse(data=required_docs, trace_id=trace_id)


@router.get("/expiring-soon", response_model=BaseResponse[list[VaultDocumentResponse]])
async def get_expiring_soon_documents(
    days: int = Query(default=30, ge=1, le=365),
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[VaultDocumentResponse]]:
    """Get documents expiring within specified days."""
    from app.contexts.compliance_vault.repository import VaultDocumentRepository

    repo = VaultDocumentRepository(service._document_repo._session)
    documents = await repo.get_expiring_soon(company_id, days)

    return BaseResponse(
        data=[VaultDocumentResponse.model_validate(doc) for doc in documents],
        trace_id=trace_id
    )


@router.get("/expired", response_model=BaseResponse[list[VaultDocumentResponse]])
async def get_expired_documents(
    service: ComplianceVaultService = Depends(get_vault_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[VaultDocumentResponse]]:
    """Get expired documents."""
    from app.contexts.compliance_vault.repository import VaultDocumentRepository

    repo = VaultDocumentRepository(service._document_repo._session)
    documents = await repo.get_expired(company_id)

    return BaseResponse(
        data=[VaultDocumentResponse.model_validate(doc) for doc in documents],
        trace_id=trace_id
    )
