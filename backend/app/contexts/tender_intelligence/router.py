from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.contexts.user_management.schemas import UserResponse
from app.database import get_session
from app.dependencies import get_current_company_id, get_current_user_id
from app.infrastructure.groq_client import GroqClient
from .repository import DocumentChunkRepository, TenderDocumentRepository
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


def get_service(session: AsyncSession = Depends(get_session)) -> TenderIntelligenceService:
    return TenderIntelligenceService(
        document_repo=TenderDocumentRepository(session),
        chunk_repo=DocumentChunkRepository(session),
        groq_client=GroqClient(),
    )


@router.post("/explain", response_model=TenderExplainResponse)
async def explain_tender(
    request: TenderExplainRequest,
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
    service: TenderIntelligenceService = Depends(get_service),
) -> TenderExplainResponse:
    """Explain tender in natural language."""
    return await service.explain_tender(request.tender_id, request.lang, company_id)


@router.post("/extract-clauses", response_model=ClauseExtractionResponse)
async def extract_clauses(
    request: ClauseExtractionRequest,
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
    service: TenderIntelligenceService = Depends(get_service),
) -> ClauseExtractionResponse:
    """Extract key clauses from tender document."""
    return await service.extract_clauses(request.tender_id, request.lang, company_id)


@router.post("/detect-risks", response_model=RiskDetectionResponse)
async def detect_risks(
    request: RiskDetectionRequest,
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
    service: TenderIntelligenceService = Depends(get_service),
) -> RiskDetectionResponse:
    """Detect risks and compliance issues in tender."""
    return await service.detect_risks(request.tender_id, request.lang, company_id)


@router.post("/document-checklist", response_model=DocumentChecklistResponse)
async def document_checklist(
    request: DocumentChecklistRequest,
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
    service: TenderIntelligenceService = Depends(get_service),
) -> DocumentChecklistResponse:
    """Generate document checklist for a tender and match against vault."""
    return await service.generate_document_checklist(request, company_id)
