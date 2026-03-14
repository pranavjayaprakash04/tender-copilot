from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.contexts.company_profile.repository import CompanyProfileRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.contexts.tender_matching.embedding_service import EmbeddingService
from app.contexts.tender_matching.repository import (
    CompanyEmbeddingRepository,
    TenderEmbeddingRepository,
)
from app.database import get_async_session
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/companies/{company_id}/generate", response_model=dict)
async def generate_company_embedding(
    company_id: UUID,
    force_refresh: bool = Query(default=False),
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Generate or update company capability embedding."""
    async with get_async_session() as session:
        # Initialize service
        embedding_service = EmbeddingService(
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyProfileRepository(session),
            tender_repo=TenderRepository(session)
        )

        try:
            # Generate embedding asynchronously
            embedding = await embedding_service.generate_company_embedding(
                company_id=company_id,
                force_refresh=force_refresh,
                trace_id=_trace_id
            )

            return {
                "company_id": str(company_id),
                "text_length": len(embedding.capabilities_text),
                "processing_time_ms": embedding.processing_time_ms,
                "created_at": embedding.created_at.isoformat(),
                "message": "Company embedding generated successfully"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate company embedding: {str(e)}"
            )


@router.post("/tenders/{tender_id}/generate", response_model=dict)
async def generate_tender_embedding(
    tender_id: UUID,
    force_refresh: bool = Query(default=False),
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Generate or update tender requirement embedding."""
    async with get_async_session() as session:
        # Initialize service
        embedding_service = EmbeddingService(
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyProfileRepository(session),
            tender_repo=TenderRepository(session)
        )

        try:
            # Generate embedding asynchronously
            embedding = await embedding_service.generate_tender_embedding(
                tender_id=tender_id,
                force_refresh=force_refresh,
                trace_id=_trace_id
            )

            return {
                "tender_id": str(tender_id),
                "text_length": len(embedding.requirements_text),
                "processing_time_ms": embedding.processing_time_ms,
                "created_at": embedding.created_at.isoformat(),
                "message": "Tender embedding generated successfully"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate tender embedding: {str(e)}"
            )


@router.post("/companies/batch", response_model=dict)
async def batch_generate_company_embeddings(
    company_ids: list[UUID] | None = None,
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Generate embeddings for multiple companies in batch."""
    async with get_async_session() as session:
        # Initialize service
        embedding_service = EmbeddingService(
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyProfileRepository(session),
            tender_repo=TenderRepository(session)
        )

        try:
            # Batch generate embeddings
            result = await embedding_service.batch_embed_companies(
                company_ids=company_ids,
                trace_id=_trace_id
            )

            return {
                "batch_id": f"batch-{_trace_id or 'unknown'}",
                "total_companies": result["total_companies"],
                "success_count": result["success_count"],
                "failed_count": result["failed_count"],
                "errors": result["errors"][:10],  # Limit errors in response
                "completed_at": result["completed_at"],
                "message": "Batch company embedding generation completed"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to batch generate company embeddings: {str(e)}"
            )


@router.post("/tenders/batch", response_model=dict)
async def batch_generate_tender_embeddings(
    tender_ids: list[UUID] | None = None,
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Generate embeddings for multiple tenders in batch."""
    async with get_async_session() as session:
        # Initialize service
        embedding_service = EmbeddingService(
            company_embedding_repo=CompanyEmbeddingRepository(session),
            tender_embedding_repo=TenderEmbeddingRepository(session),
            company_repo=CompanyProfileRepository(session),
            tender_repo=TenderRepository(session)
        )

        try:
            # Batch generate embeddings
            result = await embedding_service.batch_embed_tenders(
                tender_ids=tender_ids,
                trace_id=_trace_id
            )

            return {
                "batch_id": f"batch-{_trace_id or 'unknown'}",
                "total_tenders": result["total_tenders"],
                "success_count": result["success_count"],
                "failed_count": result["failed_count"],
                "errors": result["errors"][:10],  # Limit errors in response
                "completed_at": result["completed_at"],
                "message": "Batch tender embedding generation completed"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to batch generate tender embeddings: {str(e)}"
            )


@router.get("/companies/{company_id}", response_model=dict)
async def get_company_embedding(
    company_id: UUID,
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Get company embedding details."""
    async with get_async_session() as session:
        company_embedding_repo = CompanyEmbeddingRepository(session)

        try:
            embedding = await company_embedding_repo.get_by_company_id(company_id)
            if not embedding:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Company embedding not found"
                )

            return {
                "company_id": str(company_id),
                "text_length": len(embedding.capabilities_text),
                "processing_time_ms": embedding.processing_time_ms,
                "created_at": embedding.created_at.isoformat(),
                "updated_at": embedding.updated_at.isoformat() if embedding.updated_at else None,
                "message": "Company embedding retrieved successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve company embedding: {str(e)}"
            )


@router.get("/tenders/{tender_id}", response_model=dict)
async def get_tender_embedding(
    tender_id: UUID,
    _current_user = Depends(get_current_user_id),
    _trace_id: str | None = None
) -> dict:
    """Get tender embedding details."""
    async with get_async_session() as session:
        tender_embedding_repo = TenderEmbeddingRepository(session)

        try:
            embedding = await tender_embedding_repo.get_by_tender_id(tender_id)
            if not embedding:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tender embedding not found"
                )

            return {
                "tender_id": str(tender_id),
                "text_length": len(embedding.requirements_text),
                "processing_time_ms": embedding.processing_time_ms,
                "created_at": embedding.created_at.isoformat(),
                "updated_at": embedding.updated_at.isoformat() if embedding.updated_at else None,
                "message": "Tender embedding retrieved successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve tender embedding: {str(e)}"
            )
