from __future__ import annotations

from uuid import UUID

from app.shared.dependencies import get_current_user
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
from app.infrastructure.groq_client import GroqClient

router = APIRouter(prefix="/matching", tags=["tender-matching"])


@router.post("/companies/{company_id}/matches", response_model=dict)
async def find_matches_for_company(
    company_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    min_score: float = Query(default=0.3, ge=0.0, le=1.0),
    _force_refresh: bool = Query(default=False),
    _current_user = Depends(get_current_user),
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
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
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
                    "match_score": match.match_score,
                    "confidence_level": match.confidence_level,
                    "match_reasons": match.match_reasons or [],
                    "gap_analysis": match.gap_analysis or {},
                    "recommendations": match.recommendations or [],
                    "industry_match": match.industry_match,
                    "size_match": match.size_match,
                    "location_match": match.location_match,
                    "value_match": match.value_match,
                    "experience_match": match.experience_match,
                    "is_viewed": match.is_viewed,
                    "is_shortlisted": match.is_shortlisted,
                    "created_at": match.created_at.isoformat()
                })

            return {
                "company_id": str(company_id),
                "matches": match_results,
                "total_matches": len(match_results),
                "min_score_used": min_score,
                "limit_used": limit,
                "processing_time_ms": sum(m.processing_time_ms or 0 for m in matches),
                "message": f"Found {len(match_results)} matching tenders"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to find matches: {str(e)}"
            )


@router.post("/tenders/{tender_id}/matches", response_model=dict)
async def find_matches_for_tender(
    tender_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    min_score: float = Query(default=0.3, ge=0.0, le=1.0),
    _force_refresh: bool = Query(default=False),
    _current_user = Depends(get_current_user),
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
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
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
                    "match_score": match.match_score,
                    "confidence_level": match.confidence_level,
                    "match_reasons": match.match_reasons or [],
                    "gap_analysis": match.gap_analysis or {},
                    "recommendations": match.recommendations or [],
                    "industry_match": match.industry_match,
                    "size_match": match.size_match,
                    "location_match": match.location_match,
                    "value_match": match.value_match,
                    "experience_match": match.experience_match,
                    "is_viewed": match.is_viewed,
                    "is_shortlisted": match.is_shortlisted,
                    "created_at": match.created_at.isoformat()
                })

            return {
                "tender_id": str(tender_id),
                "matches": match_results,
                "total_matches": len(match_results),
                "min_score_used": min_score,
                "limit_used": limit,
                "processing_time_ms": sum(m.processing_time_ms or 0 for m in matches),
                "message": f"Found {len(match_results)} matching companies"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to find matches: {str(e)}"
            )


@router.post("/similarity/{company_id}/{tender_id}", response_model=dict)
async def calculate_similarity(
    company_id: UUID,
    tender_id: UUID,
    _current_user = Depends(get_current_user),
    _trace_id: str | None = None
) -> dict:
    """Calculate cosine similarity between a company and tender."""
    async with get_async_session() as session:
        # Initialize service
        matching_service = TenderMatchingService(
            match_repo=TenderMatchRepository(session),
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyRepository(session),
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
        )

        try:
            # Calculate similarity asynchronously
            similarity = await matching_service.calculate_cosine_similarity(
                company_id=company_id,
                tender_id=tender_id,
                trace_id=_trace_id
            )

            return {
                "company_id": str(company_id),
                "tender_id": str(tender_id),
                "similarity_score": similarity,
                "similarity_percentage": similarity * 100,
                "match_quality": "high" if similarity >= 0.8 else "medium" if similarity >= 0.6 else "low",
                "message": f"Similarity calculated: {similarity:.3f}"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to calculate similarity: {str(e)}"
            )


@router.post("/embeddings/companies/{company_id}/generate", response_model=dict)
async def generate_company_embedding(
    company_id: UUID,
    _force_refresh: bool = Query(default=False),
    _current_user = Depends(get_current_user),
    _trace_id: str | None = None
) -> dict:
    """Generate or update company capability embedding."""
    async with get_async_session() as session:
        # Initialize service
        matching_service = TenderMatchingService(
            match_repo=TenderMatchRepository(session),
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyRepository(session),
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
        )

        try:
            # Generate embedding asynchronously
            embedding = await matching_service.generate_company_embedding(
                company_id=company_id,
                force_refresh=_force_refresh,
                trace_id=_trace_id
            )

            return {
                "company_id": str(company_id),
                "embedding_model": embedding.embedding_model,
                "embedding_version": embedding.embedding_version,
                "text_length": embedding.text_length,
                "word_count": embedding.word_count,
                "processing_time_ms": embedding.processing_time_ms,
                "last_updated_at": embedding.last_updated_at.isoformat(),
                "message": "Company embedding generated successfully"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate company embedding: {str(e)}"
            )


@router.post("/embeddings/tenders/{tender_id}/generate", response_model=dict)
async def generate_tender_embedding(
    tender_id: UUID,
    _force_refresh: bool = Query(default=False),
    _current_user = Depends(get_current_user),
    _trace_id: str | None = None
) -> dict:
    """Generate or update tender requirement embedding."""
    async with get_async_session() as session:
        # Initialize service
        matching_service = TenderMatchingService(
            match_repo=TenderMatchRepository(session),
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyRepository(session),
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
        )

        try:
            # Generate embedding asynchronously
            embedding = await matching_service.generate_tender_embedding(
                tender_id=tender_id,
                force_refresh=_force_refresh,
                trace_id=_trace_id
            )

            return {
                "tender_id": str(tender_id),
                "embedding_model": embedding.embedding_model,
                "embedding_version": embedding.embedding_version,
                "text_length": embedding.text_length,
                "word_count": embedding.word_count,
                "processing_time_ms": embedding.processing_time_ms,
                "last_updated_at": embedding.last_updated_at.isoformat(),
                "message": "Tender embedding generated successfully"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate tender embedding: {str(e)}"
            )


@router.post("/matches/{company_id}/{tender_id}", response_model=dict)
async def create_match_record(
    company_id: UUID,
    tender_id: UUID,
    _current_user = Depends(get_current_user),
    _trace_id: str | None = None
) -> dict:
    """Create a detailed match record with analysis."""
    async with get_async_session() as session:
        # Initialize service
        matching_service = TenderMatchingService(
            match_repo=TenderMatchRepository(session),
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyRepository(session),
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
        )

        try:
            # Create match record asynchronously
            match = await matching_service.create_match_record(
                company_id=company_id,
                tender_id=tender_id,
                trace_id=_trace_id
            )

            return {
                "match_id": str(match.id),
                "company_id": str(match.company_id),
                "tender_id": str(match.tender_id),
                "match_score": match.match_score,
                "confidence_level": match.confidence_level,
                "match_reasons": match.match_reasons or [],
                "gap_analysis": match.gap_analysis or {},
                "recommendations": match.recommendations or [],
                "industry_match": match.industry_match,
                "size_match": match.size_match,
                "location_match": match.location_match,
                "value_match": match.value_match,
                "experience_match": match.experience_match,
                "processing_time_ms": match.processing_time_ms,
                "created_at": match.created_at.isoformat(),
                "message": "Match record created successfully"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create match record: {str(e)}"
            )


@router.get("/companies/{company_id}/matches", response_model=dict)
async def get_company_matches(
    company_id: UUID,
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    is_shortlisted: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _current_user = Depends(get_current_user),
    _trace_id: str | None = None
) -> dict:
    """Get existing matches for a company with pagination and filtering."""
    async with get_async_session() as session:
        try:
            match_repo = TenderMatchRepository(session)

            # Get matches with pagination
            matches, total = await match_repo.get_by_company(
                company_id=company_id,
                min_score=min_score,
                is_shortlisted=is_shortlisted,
                page=page,
                page_size=page_size
            )

            # Format response
            match_results = []
            for match in matches:
                match_results.append({
                    "match_id": str(match.id),
                    "tender_id": str(match.tender_id),
                    "match_score": match.match_score,
                    "confidence_level": match.confidence_level,
                    "match_reasons": match.match_reasons or [],
                    "gap_analysis": match.gap_analysis or {},
                    "recommendations": match.recommendations or [],
                    "is_viewed": match.is_viewed,
                    "is_shortlisted": match.is_shortlisted,
                    "user_rating": match.user_rating,
                    "created_at": match.created_at.isoformat(),
                    "updated_at": match.updated_at.isoformat()
                })

            return {
                "company_id": str(company_id),
                "matches": match_results,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "pages": (total + page_size - 1) // page_size
                },
                "filters": {
                    "min_score": min_score,
                    "is_shortlisted": is_shortlisted
                }
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get company matches: {str(e)}"
            )


@router.post("/matches/{match_id}/shortlist", response_model=dict)
async def shortlist_match(
    match_id: UUID,
    _current_user = Depends(get_current_user),
    _trace_id: str | None = None
) -> dict:
    """Shortlist a match for follow-up."""
    async with get_async_session() as session:
        try:
            match_repo = TenderMatchRepository(session)

            # Update match to shortlisted
            await match_repo.update_shortlist(match_id, True)

            return {
                "match_id": str(match_id),
                "is_shortlisted": True,
                "message": "Match shortlisted successfully"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to shortlist match: {str(e)}"
            )


@router.post("/matches/{match_id}/rate", response_model=dict)
async def rate_match(
    match_id: UUID,
    rating: int = Query(..., ge=1, le=5),
    feedback: str | None = None,
    _current_user = Depends(get_current_user),
    _trace_id: str | None = None
) -> dict:
    """Rate a match and provide feedback."""
    async with get_async_session() as session:
        try:
            match_repo = TenderMatchRepository(session)

            # Update match rating and feedback
            await match_repo.update_rating(match_id, rating, feedback)

            return {
                "match_id": str(match_id),
                "user_rating": rating,
                "user_feedback": feedback,
                "message": "Match rated successfully"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to rate match: {str(e)}"
            )
