from uuid import UUID
from fastapi import APIRouter, Depends
from app.contexts.user_management.schemas import UserResponse
from app.dependencies import get_current_company_id, get_current_user_id
from .schemas import (
    ClauseExtractionRequest,
    ClauseExtractionResponse,
    DocumentChecklistRequest,
    DocumentChecklistResponse,
    RiskDetectionRequest,
    RiskDetectionResponse,
    TenderExplainRequest,
    TenderExplainResponse,
)
from .service import TenderIntelligenceService

router = APIRouter(prefix="/intelligence", tags=["tender_intelligence"])


@router.post("/explain", response_model=TenderExplainResponse)
async def explain_tender(
    request: TenderExplainRequest,
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
) -> TenderExplainResponse:
    """Explain tender in natural language."""
    service = TenderIntelligenceService()
    return await service.explain_tender(request.tender_id, request.lang, company_id)


@router.post("/extract-clauses", response_model=ClauseExtractionResponse)
async def extract_clauses(
    request: ClauseExtractionRequest,
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
) -> ClauseExtractionResponse:
    """Extract key clauses from tender document."""
    service = TenderIntelligenceService()
    return await service.extract_clauses(request.tender_id, request.lang, company_id)


@router.post("/detect-risks", response_model=RiskDetectionResponse)
async def detect_risks(
    request: RiskDetectionRequest,
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
) -> RiskDetectionResponse:
    """Detect risks and compliance issues in tender."""
    service = TenderIntelligenceService()
    return await service.detect_risks(request.tender_id, request.lang, company_id)


@router.post("/document-checklist", response_model=DocumentChecklistResponse)
async def document_checklist(
    request: DocumentChecklistRequest,
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
) -> DocumentChecklistResponse:
    """Generate document checklist for a tender and match against vault."""
    service = TenderIntelligenceService()
    return await service.generate_document_checklist(request, company_id)
