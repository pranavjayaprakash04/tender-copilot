from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.bid_lifecycle.models import BidStatus
from app.contexts.bid_lifecycle.repository import (
    BidFollowUpRepository,
    BidOutcomeRecordRepository,
    BidPaymentRepository,
    BidRepository,
)
from app.contexts.bid_lifecycle.schemas import (
    BidCreate,
    BidFollowUpCreate,
    BidFollowUpResponse,
    BidFollowUpUpdate,
    BidListResponse,
    BidOutcomeRecordCreate,
    BidOutcomeRecordResponse,
    BidOutcomeRecordUpdate,
    BidPaymentCreate,
    BidPaymentResponse,
    BidPaymentUpdate,
    BidResponse,
    BidSearchFilters,
    BidStatsResponse,
    BidStatusTransition,
    BidUpdate,
)
from app.contexts.bid_lifecycle.service import BidLifecycleService
from app.database import get_async_session
from app.dependencies import get_current_company_id, get_current_user_id, get_trace_id
from app.infrastructure.groq_client import GroqClient

router = APIRouter(prefix="/bids", tags=["bid-lifecycle"])


# ── Dependency ────────────────────────────────────────────────────────────────

async def get_bid_service(
    session: AsyncSession = Depends(get_async_session),
) -> BidLifecycleService:
    return BidLifecycleService(
        bid_repo=BidRepository(session),
        outcome_repo=BidOutcomeRecordRepository(session),
        payment_repo=BidPaymentRepository(session),
        follow_up_repo=BidFollowUpRepository(session),
        groq_client=GroqClient(),
    )


# ── Bids ──────────────────────────────────────────────────────────────────────

@router.post("", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def create_bid(
    bid_data: BidCreate,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    """Create a new bid from a tender."""
    # Enforce company_id from auth context (ignore what frontend sends)
    bid_data.company_id = UUID(company_id)
    try:
        return await service.create_bid(bid_data, trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=BidListResponse)
async def list_bids(
    search: str | None = Query(None),
    bid_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    """List all bids for the authenticated company."""
    filters = BidSearchFilters(
        search_query=search,
        status=BidStatus(bid_status) if bid_status else None,
    )
    return await service.list_bids(
        company_id=UUID(company_id),
        filters=filters,
        page=page,
        page_size=page_size,
        trace_id=trace_id,
    )


@router.get("/stats", response_model=BidStatsResponse)
async def get_bid_stats(
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    """Get bid statistics for the authenticated company."""
    return await service.get_bid_stats(company_id=UUID(company_id), trace_id=trace_id)


@router.get("/{bid_id}", response_model=BidResponse)
async def get_bid(
    bid_id: UUID,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    """Get a bid by ID."""
    try:
        return await service.get_bid(bid_id, UUID(company_id), trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{bid_id}", response_model=BidResponse)
async def update_bid(
    bid_id: UUID,
    update_data: BidUpdate,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    """Update a bid."""
    try:
        return await service.update_bid(bid_id, UUID(company_id), update_data, trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{bid_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bid(
    bid_id: UUID,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    """Delete a draft bid."""
    try:
        await service.delete_bid(bid_id, UUID(company_id), trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{bid_id}/transition", response_model=BidResponse)
async def transition_bid_status(
    bid_id: UUID,
    transition: BidStatusTransition,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    """Transition a bid to a new status."""
    try:
        bid, _ = await service.transition_bid_status(
            bid_id, UUID(company_id), transition, trace_id=trace_id
        )
        return bid
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Payments ──────────────────────────────────────────────────────────────────

@router.post("/{bid_id}/payments", response_model=BidPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    bid_id: UUID,
    payment_data: BidPaymentCreate,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    payment_data.bid_id = bid_id
    try:
        return await service.create_payment(payment_data, UUID(company_id), trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{bid_id}/payments", response_model=list[BidPaymentResponse])
async def get_bid_payments(
    bid_id: UUID,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    return await service.get_bid_payments(bid_id, UUID(company_id), trace_id=trace_id)


@router.patch("/{bid_id}/payments/{payment_id}", response_model=BidPaymentResponse)
async def update_payment(
    bid_id: UUID,
    payment_id: UUID,
    update_data: BidPaymentUpdate,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    try:
        return await service.update_payment(payment_id, UUID(company_id), update_data, trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Outcomes ──────────────────────────────────────────────────────────────────

@router.post("/{bid_id}/outcomes", response_model=BidOutcomeRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_outcome(
    bid_id: UUID,
    outcome_data: BidOutcomeRecordCreate,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    outcome_data.bid_id = bid_id
    try:
        return await service.create_outcome_record(outcome_data, UUID(company_id), trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{bid_id}/outcomes/{outcome_id}", response_model=BidOutcomeRecordResponse)
async def update_outcome(
    bid_id: UUID,
    outcome_id: UUID,
    update_data: BidOutcomeRecordUpdate,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    try:
        return await service.update_outcome_record(outcome_id, UUID(company_id), update_data, trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Follow-ups ────────────────────────────────────────────────────────────────

@router.post("/{bid_id}/follow-ups", response_model=BidFollowUpResponse, status_code=status.HTTP_201_CREATED)
async def create_follow_up(
    bid_id: UUID,
    follow_up_data: BidFollowUpCreate,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    follow_up_data.bid_id = bid_id
    try:
        return await service.create_follow_up(follow_up_data, UUID(company_id), trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{bid_id}/follow-ups", response_model=list[BidFollowUpResponse])
async def get_bid_follow_ups(
    bid_id: UUID,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    return await service.get_bid_follow_ups(bid_id, UUID(company_id), trace_id=trace_id)


@router.patch("/{bid_id}/follow-ups/{follow_up_id}", response_model=BidFollowUpResponse)
async def update_follow_up(
    bid_id: UUID,
    follow_up_id: UUID,
    update_data: BidFollowUpUpdate,
    service: BidLifecycleService = Depends(get_bid_service),
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
):
    try:
        return await service.update_follow_up(follow_up_id, UUID(company_id), update_data, trace_id=trace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
