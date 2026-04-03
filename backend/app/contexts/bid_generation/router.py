from __future__ import annotations

from typing import Any
from uuid import UUID

from app.shared.dependencies import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status

from app.contexts.bid_generation.repository import (
    BidGenerationAnalyticsRepository,
    BidGenerationRepository,
    BidTemplateRepository,
)
from app.contexts.bid_generation.service import BidGenerationService
from app.contexts.bid_generation.tasks import generate_bid_task
from app.contexts.tender_discovery.repository import TenderRepository
from app.database import get_async_session
from app.infrastructure.groq_client import GroqClient

router = APIRouter(prefix="/bids", tags=["bid-generation"])


@router.post("/generate", response_model=dict)
async def generate_bid(
    tender_id: UUID,
    bid_type: str = "technical",
    language: str = "en",
    bid_title: str | None = None,
    bid_description: str | None = None,
    template_id: UUID | None = None,
    customization: dict[str, Any] | None = None,
    current_user = Depends(get_current_user),
    trace_id: str | None = None
) -> dict:
    """Generate bid content asynchronously and return task ID immediately."""
    async with get_async_session() as session:
        # Initialize service
        bid_service = BidGenerationService(
            bid_repo=BidGenerationRepository(session),
            template_repo=BidTemplateRepository(session),
            analytics_repo=BidGenerationAnalyticsRepository(session),
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
        )

        try:
            # Create bid generation record
            bid_generation = await bid_service.initiate_bid_generation(
                tender_id=tender_id,
                company_id=current_user.company_id,
                bid_type=bid_type,
                language=language,
                bid_title=bid_title,
                bid_description=bid_description,
                template_id=template_id,
                customization=customization,
                trace_id=trace_id
            )

            # Trigger async Celery task - return task_id immediately
            task = generate_bid_task.delay(
                bid_id=str(bid_generation.id),
                company_id=str(current_user.company_id),
                tender_id=str(tender_id),
                lang_code=language
            )

            return {
                "task_id": task.id,
                "bid_id": str(bid_generation.id),
                "status": "pending",
                "message": "Bid generation started. Check status using the task_id.",
                "estimated_completion": bid_generation.estimated_completion_time.isoformat() if bid_generation.estimated_completion_time else None
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start bid generation: {str(e)}"
            )


@router.get("/{task_id}/status", response_model=dict)
async def get_bid_generation_status(
    task_id: str,
    current_user = Depends(get_current_user),
    trace_id: str | None = None
) -> dict:
    """Check the status of a bid generation task."""
    async with get_async_session() as session:
        # Initialize service
        bid_service = BidGenerationService(
            bid_repo=BidGenerationRepository(session),
            template_repo=BidTemplateRepository(session),
            analytics_repo=BidGenerationAnalyticsRepository(session),
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
        )

        try:
            # Check Celery task state
            from celery.result import AsyncResult
            task_result = AsyncResult(task_id)

            if task_result.state == "PENDING":
                return {
                    "task_id": task_id,
                    "status": "pending",
                    "progress": 0.0,
                    "message": "Task is queued and waiting to start."
                }
            elif task_result.state == "PROGRESS":
                return {
                    "task_id": task_id,
                    "status": "generating",
                    "progress": 50.0,
                    "message": "Bid generation is in progress."
                }
            elif task_result.state == "SUCCESS":
                # Task completed successfully
                result = task_result.get()

                # Get bid generation details
                bid_generation = await bid_service.get_bid_generation_status(
                    result["bid_id"], current_user.company_id, trace_id
                )

                return {
                    "task_id": task_id,
                    "status": "completed",
                    "progress": 100.0,
                    "bid_id": result["bid_id"],
                    "bid_type": bid_generation.bid_type,
                    "processing_time_ms": result.get("processing_time_ms"),
                    "confidence_score": result.get("confidence_score"),
                    "completed_at": result.get("completed_at"),
                    "bid_content": bid_generation.bid_content,
                    "executive_summary": bid_generation.executive_summary,
                    "technical_proposal": bid_generation.technical_proposal,
                    "financial_proposal": bid_generation.financial_proposal,
                    "message": "Bid generation completed successfully."
                }
            elif task_result.state == "FAILURE":
                # Task failed
                result = task_result.get()

                return {
                    "task_id": task_id,
                    "status": "failed",
                    "progress": 0.0,
                    "error": result.get("error", "Unknown error"),
                    "retry_count": result.get("retry_count", 0),
                    "failed_at": result.get("failed_at"),
                    "message": "Bid generation failed."
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "unknown",
                    "progress": 0.0,
                    "message": f"Task state: {task_result.state}"
                }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check task status: {str(e)}"
            )


@router.get("/", response_model=dict)
async def list_bid_generations(
    bid_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user = Depends(get_current_user),
    trace_id: str | None = None
) -> dict:
    """List bid generations for the current user's company."""
    async with get_async_session() as session:
        # Initialize service
        bid_service = BidGenerationService(
            bid_repo=BidGenerationRepository(session),
            template_repo=BidTemplateRepository(session),
            analytics_repo=BidGenerationAnalyticsRepository(session),
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
        )

        try:
            bid_generations, total = await bid_service.list_bid_generations(
                company_id=current_user.company_id,
                bid_type=bid_type,
                status=status,
                page=page,
                page_size=page_size,
                trace_id=trace_id
            )

            return {
                "bid_generations": [
                    {
                        "id": str(bg.id),
                        "task_id": bg.task_id,
                        "bid_type": bg.bid_type,
                        "language": bg.language,
                        "bid_title": bg.bid_title,
                        "status": bg.status,
                        "created_at": bg.created_at.isoformat(),
                        "completed_at": bg.generation_completed_at.isoformat() if bg.generation_completed_at else None,
                        "processing_time_ms": bg.processing_time_ms,
                        "confidence_score": bg.confidence_score,
                        "user_rating": bg.user_rating,
                        "is_approved": bg.is_approved
                    }
                    for bg in bid_generations
                ],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "pages": (total + page_size - 1) // page_size
                }
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list bid generations: {str(e)}"
            )


@router.post("/{bid_id}/cancel", response_model=dict)
async def cancel_bid_generation(
    bid_id: UUID,
    current_user = Depends(get_current_user),
    trace_id: str | None = None
) -> dict:
    """Cancel a bid generation task."""
    async with get_async_session() as session:
        # Initialize service
        bid_service = BidGenerationService(
            bid_repo=BidGenerationRepository(session),
            template_repo=BidTemplateRepository(session),
            analytics_repo=BidGenerationAnalyticsRepository(session),
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
        )

        try:
            bid_generation = await bid_service.cancel_bid_generation(
                task_id=str(bid_id),
                company_id=current_user.company_id,
                trace_id=trace_id
            )

            return {
                "bid_id": str(bid_generation.id),
                "status": "cancelled",
                "message": "Bid generation cancelled successfully."
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel bid generation: {str(e)}"
            )


@router.post("/{bid_id}/retry", response_model=dict)
async def retry_bid_generation(
    bid_id: UUID,
    current_user = Depends(get_current_user),
    trace_id: str | None = None
) -> dict:
    """Retry a failed bid generation."""
    async with get_async_session() as session:
        # Initialize service
        bid_service = BidGenerationService(
            bid_repo=BidGenerationRepository(session),
            template_repo=BidTemplateRepository(session),
            analytics_repo=BidGenerationAnalyticsRepository(session),
            tender_repo=TenderRepository(session),
            groq_client=GroqClient()
        )

        try:
            bid_generation = await bid_service.retry_failed_generation(
                task_id=str(bid_id),
                company_id=current_user.company_id,
                trace_id=trace_id
            )

            # Trigger new Celery task
            task = generate_bid_task.delay(
                bid_id=str(bid_generation.id),
                company_id=str(current_user.company_id),
                tender_id=str(bid_generation.tender_id),
                lang_code=bid_generation.language
            )

            return {
                "task_id": task.id,
                "bid_id": str(bid_generation.id),
                "status": "pending",
                "retry_count": bid_generation.retry_count,
                "message": "Bid generation retry started."
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retry bid generation: {str(e)}"
            )
