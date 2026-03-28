from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.contexts.bid_intelligence.schemas import (
    CompetitorAnalysisRequest,
    CompetitorAnalysisResponse,
    WinProbabilityRequest,
    WinProbabilityResponse,
)
from app.contexts.bid_intelligence.service import BidIntelligenceService
from app.contexts.company_profile.repository import CompanyProfileRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.database import get_async_session
from app.dependencies import get_current_company_id, get_current_user_id
from app.infrastructure.groq_client import GroqClient

router = APIRouter(prefix="/intelligence/bid", tags=["bid_intelligence"])


async def get_bid_intelligence_service(
    session: AsyncSession = Depends(get_async_session),
) -> BidIntelligenceService:
    groq_client = GroqClient()
    tender_repo = TenderRepository(session)
    company_repo = CompanyProfileRepository(session)
    return BidIntelligenceService(groq_client, tender_repo, company_repo, session)


@router.post("/analyze-competitors", response_model=CompetitorAnalysisResponse)
async def analyze_competitors(
    req: CompetitorAnalysisRequest,
    service: BidIntelligenceService = Depends(get_bid_intelligence_service),
    _current_user_id: str = Depends(get_current_user_id),
    _company_id: str = Depends(get_current_company_id),
) -> CompetitorAnalysisResponse:
    try:
        return await service.analyze_competitors(req)  # company_id is inside req
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/win-probability", response_model=WinProbabilityResponse)
async def calculate_win_probability(
    req: WinProbabilityRequest,
    service: BidIntelligenceService = Depends(get_bid_intelligence_service),
    _current_user_id: str = Depends(get_current_user_id),
    _company_id: str = Depends(get_current_company_id),
) -> WinProbabilityResponse:
    try:
        return await service.calculate_win_probability(req)  # company_id is inside req
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/market-price/{category}")
async def get_market_price(
    category: str,
    service: BidIntelligenceService = Depends(get_bid_intelligence_service),
    _current_user_id: str = Depends(get_current_user_id),
    _company_id: str = Depends(get_current_company_id),
) -> dict[str, Any] | None:
    try:
        return await service.get_market_price(category)  # no company_id needed
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
