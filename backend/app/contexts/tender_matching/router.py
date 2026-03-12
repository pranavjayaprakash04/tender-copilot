from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.contexts.company_profile.repository import CompanyRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.contexts.tender_matching.repository import (
    CompanyEmbeddingRepository,
    TenderEmbeddingRepository,
    TenderMatchRepository,
)
from app.contexts.tender_matching.service import TenderMatchingService
from app.database import get_async_session
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/matching", tags=["tender-matching"])


@router.post("/companies/{company_id}/matches", response_model=dict)
async def find_matches_for_company(
    company_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    min_score: float = Query(default=0.3, ge=0.0, le=1.0),
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Find matching tenders for a company using pgvector cosine similarity."""
    async with get_async_session() as session:
        # Initialize service
        matching_service = TenderMatchingService(
            match_repo=TenderMatchRepository(session),
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyRepository(session),
            tender_repo=TenderRepository(session)
        )

        try:
            # Find matches asynchronously
            matches = await matching_service.find_matches_for_company(
                company_id=company_id,
                limit=limit,
                min_score=min_score,
                trace_id=_trace_id
            )

            # Format response
            match_results = []
            for match in matches:
                match_results.append({
                    "tender_id": str(match.tender_id),
                    "match_score": float(match.match_score),
                    "confidence_level": match.confidence_level,
                    "industry_match": float(match.industry_match),
                    "size_match": float(match.size_match),
                    "location_match": float(match.location_match),
                    "value_match": float(match.value_match),
                    "experience_match": float(match.experience_match),
                    "match_reasons": match.match_reasons,
                    "gap_analysis": match.gap_analysis,
                    "recommendations": match.recommendations,
                    "created_at": match.created_at.isoformat()
                })

            return {
                "company_id": str(company_id),
                "total_matches": len(match_results),
                "search_params": {
                    "limit": limit,
                    "min_score": min_score
                },
                "matches": match_results,
                "message": f"Found {len(match_results)} matching tenders"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to find matches for company: {str(e)}"
            )


@router.post("/tenders/{tender_id}/matches", response_model=dict)
async def find_matches_for_tender(
    tender_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    min_score: float = Query(default=0.3, ge=0.0, le=1.0),
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Find matching companies for a tender using pgvector cosine similarity."""
    async with get_async_session() as session:
        # Initialize service
        matching_service = TenderMatchingService(
            match_repo=TenderMatchRepository(session),
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyRepository(session),
            tender_repo=TenderRepository(session)
        )

        try:
            # Find matches asynchronously
            matches = await matching_service.find_matches_for_tender(
                tender_id=tender_id,
                limit=limit,
                min_score=min_score,
                trace_id=_trace_id
            )

            # Format response
            match_results = []
            for match in matches:
                match_results.append({
                    "company_id": str(match.company_id),
                    "match_score": float(match.match_score),
                    "confidence_level": match.confidence_level,
                    "industry_match": float(match.industry_match),
                    "size_match": float(match.size_match),
                    "location_match": float(match.location_match),
                    "value_match": float(match.value_match),
                    "experience_match": float(match.experience_match),
                    "match_reasons": match.match_reasons,
                    "gap_analysis": match.gap_analysis,
                    "recommendations": match.recommendations,
                    "created_at": match.created_at.isoformat()
                })

            return {
                "tender_id": str(tender_id),
                "total_matches": len(match_results),
                "search_params": {
                    "limit": limit,
                    "min_score": min_score
                },
                "matches": match_results,
                "message": f"Found {len(match_results)} matching companies"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to find matches for tender: {str(e)}"
            )


@router.post("/matches", response_model=dict)
async def create_match_record(
    company_id: UUID,
    tender_id: UUID,
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Create a match record."""
    async with get_async_session() as session:
        # Initialize service
        matching_service = TenderMatchingService(
            match_repo=TenderMatchRepository(session),
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyRepository(session),
            tender_repo=TenderRepository(session)
        )

        try:
            # Create match record
            match = await matching_service.create_match_record(
                company_id=company_id,
                tender_id=tender_id,
                trace_id=_trace_id
            )

            return {
                "match_id": str(match.id),
                "company_id": str(match.company_id),
                "tender_id": str(match.tender_id),
                "match_score": float(match.match_score),
                "confidence_level": match.confidence_level,
                "industry_match": float(match.industry_match),
                "size_match": float(match.size_match),
                "location_match": float(match.location_match),
                "value_match": float(match.value_match),
                "experience_match": float(match.experience_match),
                "match_reasons": match.match_reasons,
                "gap_analysis": match.gap_analysis,
                "recommendations": match.recommendations,
                "created_at": match.created_at.isoformat(),
                "message": "Match record created successfully"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create match record: {str(e)}"
            )


@router.get("/matches/{match_id}", response_model=dict)
async def get_match_record(
    match_id: UUID,
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Get a specific match record by ID."""
    async with get_async_session() as session:
        match_repo = TenderMatchRepository(session)

        try:
            match = await match_repo.get_by_id(match_id)
            if not match:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Match record not found"
                )

            return {
                "match_id": str(match.id),
                "company_id": str(match.company_id),
                "tender_id": str(match.tender_id),
                "match_score": float(match.match_score),
                "confidence_level": match.confidence_level,
                "industry_match": float(match.industry_match),
                "size_match": float(match.size_match),
                "location_match": float(match.location_match),
                "value_match": float(match.value_match),
                "experience_match": float(match.experience_match),
                "match_reasons": match.match_reasons,
                "gap_analysis": match.gap_analysis,
                "recommendations": match.recommendations,
                "created_at": match.created_at.isoformat(),
                "updated_at": match.updated_at.isoformat() if match.updated_at else None,
                "message": "Match record retrieved successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve match record: {str(e)}"
            )
