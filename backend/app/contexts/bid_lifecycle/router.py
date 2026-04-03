from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.contexts.bid_lifecycle.models import (
    BidStatus,
)
from app.contexts.bid_lifecycle.schemas import (
    BidBulkStatusTransition,
    BidBulkUpdate,
    BidCreate,
    BidFollowUpCreate,
    BidFollowUpResponse,
    BidFollowUpUpdate,
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
    LossAnalysisRequest,
    LossAnalysisResponse,
    PaymentFollowUpRequest,
    PaymentFollowUpResponse,
)
from app.contexts.bid_lifecycle.service import BidLifecycleService
from app.contexts.bid_lifecycle.tasks import (
    analyze_bid_loss_task,
    create_payment_schedule_task,
    process_payment_follow_ups_task,
)
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

router = APIRouter(prefix="/bids", tags=["bid-lifecycle"])


def get_bid_lifecycle_service(
    session = Depends(get_db_session)
) -> BidLifecycleService:
    """Dependency to get bid lifecycle service."""
    from app.contexts.bid_lifecycle.repository import (
        BidFollowUpRepository,
        BidOutcomeRecordRepository,
        BidPaymentRepository,
        BidRepository,
    )
    from app.infrastructure.groq_client import GroqClient

    return BidLifecycleService(
        bid_repo=BidRepository(session),
        outcome_repo=BidOutcomeRecordRepository(session),
        payment_repo=BidPaymentRepository(session),
        follow_up_repo=BidFollowUpRepository(session),
        groq_client=GroqClient()
    )


# Bid CRUD Operations
@router.post("", response_model=BaseResponse[BidResponse])
async def create_bid(
    bid_data: BidCreate,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidResponse]:
    """Create a new bid."""
    bid = await service.create_bid(bid_data, company_id, trace_id)
    return BaseResponse(data=bid, trace_id=trace_id)


@router.get("", response_model=PaginatedResponse[BidResponse])
async def list_bids(
    search_query: str | None = Query(None),
    status: BidStatus | None = Query(None),
    tender_id: UUID | None = Query(None),
    lead_bidder: str | None = Query(None),
    bid_manager: str | None = Query(None),
    min_amount: float | None = Query(None),
    max_amount: float | None = Query(None),
    submission_date_from: str | None = Query(None),
    submission_date_to: str | None = Query(None),
    deadline_from: str | None = Query(None),
    deadline_to: str | None = Query(None),
    is_editable: bool | None = Query(None),
    is_submittable: bool | None = Query(None),
    has_overdue_payments: bool | None = Query(None),
    pagination: dict = Depends(get_pagination_params),
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> PaginatedResponse[BidResponse]:
    """List bids with filters."""
    from datetime import datetime

    filters = BidSearchFilters(
        search_query=search_query,
        status=status,
        tender_id=tender_id,
        lead_bidder=lead_bidder,
        bid_manager=bid_manager,
        min_amount=min_amount,
        max_amount=max_amount,
        submission_date_from=datetime.fromisoformat(submission_date_from.replace('Z', '+00:00')) if submission_date_from else None,
        submission_date_to=datetime.fromisoformat(submission_date_to.replace('Z', '+00:00')) if submission_date_to else None,
        deadline_from=datetime.fromisoformat(deadline_from.replace('Z', '+00:00')) if deadline_from else None,
        deadline_to=datetime.fromisoformat(deadline_to.replace('Z', '+00:00')) if deadline_to else None,
        is_editable=is_editable,
        is_submittable=is_submittable,
        has_overdue_payments=has_overdue_payments
    )

    bids = await service.list_bids(
        company_id, filters, pagination["page"], pagination["page_size"], trace_id
    )

    return PaginatedResponse(
        data=bids.bids,
        pagination={
            "page": pagination["page"],
            "page_size": pagination["page_size"],
            "total_items": bids.total,
            "total_pages": (bids.total + pagination["page_size"] - 1) // pagination["page_size"],
            "has_next": pagination["page"] * pagination["page_size"] < bids.total,
            "has_previous": pagination["page"] > 1
        },
        trace_id=trace_id
    )


@router.get("/{bid_id}", response_model=BaseResponse[BidResponse])
async def get_bid(
    bid_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidResponse]:
    """Get a specific bid."""
    bid = await service.get_bid(bid_id, company_id, trace_id)
    return BaseResponse(data=bid, trace_id=trace_id)


@router.put("/{bid_id}", response_model=BaseResponse[BidResponse])
async def update_bid(
    bid_id: UUID,
    update_data: BidUpdate,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidResponse]:
    """Update a bid."""
    bid = await service.update_bid(bid_id, company_id, update_data, trace_id)
    return BaseResponse(data=bid, trace_id=trace_id)


@router.delete("/{bid_id}")
async def delete_bid(
    bid_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Delete a bid."""
    await service.delete_bid(bid_id, company_id, trace_id)
    return JSONResponse(content={"message": "Bid deleted successfully"}, status_code=200)


# Status Transitions
@router.post("/{bid_id}/transition", response_model=BaseResponse[dict])
async def transition_bid_status(
    bid_id: UUID,
    status_transition: BidStatusTransition,
    outcome_data: BidOutcomeRecordCreate | None = None,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[dict]:
    """Transition bid status with outcome record if required."""
    bid_response, outcome_response = await service.transition_bid_status(
        bid_id, company_id, status_transition, outcome_data, trace_id
    )

    response_data = {"bid": bid_response.model_dump()}
    if outcome_response:
        response_data["outcome"] = outcome_response.model_dump()

    return BaseResponse(data=response_data, trace_id=trace_id)


@router.get("/stats/overview", response_model=BaseResponse[BidStatsResponse])
async def get_bid_stats(
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidStatsResponse]:
    """Get bid statistics."""
    stats = await service.get_bid_stats(company_id, trace_id)
    return BaseResponse(data=stats, trace_id=trace_id)


# Bulk Operations
@router.put("/bulk/update", response_model=BaseResponse[list[BidResponse]])
async def bulk_update_bids(
    bulk_data: BidBulkUpdate,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[BidResponse]]:
    """Bulk update bids."""
    bids = await service.bulk_update_bids(bulk_data, company_id, trace_id)
    return BaseResponse(data=bids, trace_id=trace_id)


@router.put("/bulk/transition", response_model=BaseResponse[list[BidResponse]])
async def bulk_transition_bids(
    bulk_data: BidBulkStatusTransition,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[BidResponse]]:
    """Bulk transition bid statuses."""
    bids = await service.bulk_transition_bids(bulk_data, company_id, trace_id)
    return BaseResponse(data=bids, trace_id=trace_id)


# Outcome Management
@router.post("/outcomes", response_model=BaseResponse[BidOutcomeRecordResponse])
async def create_outcome_record(
    outcome_data: BidOutcomeRecordCreate,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidOutcomeRecordResponse]:
    """Create a bid outcome record."""
    outcome = await service.create_outcome_record(outcome_data, company_id, trace_id)
    return BaseResponse(data=outcome, trace_id=trace_id)


@router.get("/outcomes/{outcome_id}", response_model=BaseResponse[BidOutcomeRecordResponse])
async def get_outcome_record(
    outcome_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidOutcomeRecordResponse]:
    """Get outcome record by ID."""
    outcome = await service.get_outcome_record(outcome_id, company_id, trace_id)
    return BaseResponse(data=outcome, trace_id=trace_id)


@router.put("/outcomes/{outcome_id}", response_model=BaseResponse[BidOutcomeRecordResponse])
async def update_outcome_record(
    outcome_id: UUID,
    update_data: BidOutcomeRecordUpdate,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidOutcomeRecordResponse]:
    """Update an outcome record."""
    outcome = await service.update_outcome_record(outcome_id, company_id, update_data, trace_id)
    return BaseResponse(data=outcome, trace_id=trace_id)


@router.delete("/outcomes/{outcome_id}")
async def delete_outcome_record(
    outcome_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Delete an outcome record."""
    await service.delete_outcome_record(outcome_id, company_id, trace_id)
    return JSONResponse(content={"message": "Outcome record deleted successfully"}, status_code=200)


# Payment Management
@router.post("/payments", response_model=BaseResponse[BidPaymentResponse])
async def create_payment(
    payment_data: BidPaymentCreate,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidPaymentResponse]:
    """Create a bid payment."""
    payment = await service.create_payment(payment_data, company_id, trace_id)
    return BaseResponse(data=payment, trace_id=trace_id)


@router.get("/payments/{payment_id}", response_model=BaseResponse[BidPaymentResponse])
async def get_payment(
    payment_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidPaymentResponse]:
    """Get payment by ID."""
    payment = await service.get_payment(payment_id, company_id, trace_id)
    return BaseResponse(data=payment, trace_id=trace_id)


@router.get("/{bid_id}/payments", response_model=BaseResponse[list[BidPaymentResponse]])
async def get_bid_payments(
    bid_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[BidPaymentResponse]]:
    """Get payments for a bid."""
    payments = await service.get_bid_payments(bid_id, company_id, trace_id)
    return BaseResponse(data=payments, trace_id=trace_id)


@router.put("/payments/{payment_id}", response_model=BaseResponse[BidPaymentResponse])
async def update_payment(
    payment_id: UUID,
    update_data: BidPaymentUpdate,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidPaymentResponse]:
    """Update a payment."""
    payment = await service.update_payment(payment_id, company_id, update_data, trace_id)
    return BaseResponse(data=payment, trace_id=trace_id)


@router.delete("/payments/{payment_id}")
async def delete_payment(
    payment_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Delete a payment."""
    await service.delete_payment(payment_id, company_id, trace_id)
    return JSONResponse(content={"message": "Payment deleted successfully"}, status_code=200)


@router.get("/payments/overdue", response_model=BaseResponse[list[BidPaymentResponse]])
async def get_overdue_payments(
    days_overdue: int = Query(0, ge=0),
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[BidPaymentResponse]]:
    """Get overdue payments."""
    payments = await service.get_overdue_payments(company_id, days_overdue, trace_id)
    return BaseResponse(data=payments, trace_id=trace_id)


@router.post("/payments/process-follow-ups", response_model=BaseResponse[PaymentFollowUpResponse])
async def process_payment_follow_ups(
    request: PaymentFollowUpRequest,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[PaymentFollowUpResponse]:
    """Process payment follow-ups for overdue payments."""
    result = await service.process_payment_follow_ups(request, company_id, trace_id)
    return BaseResponse(data=result, trace_id=trace_id)


# Follow-up Management
@router.post("/follow-ups", response_model=BaseResponse[BidFollowUpResponse])
async def create_follow_up(
    follow_up_data: BidFollowUpCreate,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidFollowUpResponse]:
    """Create a follow-up."""
    follow_up = await service.create_follow_up(follow_up_data, company_id, trace_id)
    return BaseResponse(data=follow_up, trace_id=trace_id)


@router.get("/follow-ups/{follow_up_id}", response_model=BaseResponse[BidFollowUpResponse])
async def get_follow_up(
    follow_up_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidFollowUpResponse]:
    """Get follow-up by ID."""
    follow_up = await service.get_follow_up(follow_up_id, company_id, trace_id)
    return BaseResponse(data=follow_up, trace_id=trace_id)


@router.get("/{bid_id}/follow-ups", response_model=BaseResponse[list[BidFollowUpResponse]])
async def get_bid_follow_ups(
    bid_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[BidFollowUpResponse]]:
    """Get follow-ups for a bid."""
    follow_ups = await service.get_bid_follow_ups(bid_id, company_id, trace_id)
    return BaseResponse(data=follow_ups, trace_id=trace_id)


@router.put("/follow-ups/{follow_up_id}", response_model=BaseResponse[BidFollowUpResponse])
async def update_follow_up(
    follow_up_id: UUID,
    update_data: BidFollowUpUpdate,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[BidFollowUpResponse]:
    """Update a follow-up."""
    follow_up = await service.update_follow_up(follow_up_id, company_id, update_data, trace_id)
    return BaseResponse(data=follow_up, trace_id=trace_id)


@router.delete("/follow-ups/{follow_up_id}")
async def delete_follow_up(
    follow_up_id: UUID,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Delete a follow-up."""
    await service.delete_follow_up(follow_up_id, company_id, trace_id)
    return JSONResponse(content={"message": "Follow-up deleted successfully"}, status_code=200)


@router.get("/follow-ups/overdue", response_model=BaseResponse[list[BidFollowUpResponse]])
async def get_overdue_follow_ups(
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[BidFollowUpResponse]]:
    """Get overdue follow-ups."""
    follow_ups = await service.get_overdue_follow_ups(company_id, trace_id)
    return BaseResponse(data=follow_ups, trace_id=trace_id)


# Analysis
@router.post("/{bid_id}/analyze-loss", response_model=BaseResponse[LossAnalysisResponse])
async def analyze_bid_loss(
    bid_id: UUID,
    request: LossAnalysisRequest,
    service: BidLifecycleService = Depends(get_bid_lifecycle_service),
    lang: LangContext = Depends(get_lang_context),
    trace_id: str = Depends(get_trace_id),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id)
) -> BaseResponse[LossAnalysisResponse]:
    """Analyze bid loss using AI."""
    request.bid_id = bid_id
    analysis = await service.analyze_loss(request, lang, trace_id, str(company_id))
    return BaseResponse(data=analysis, trace_id=trace_id)


# Background Tasks
@router.post("/{bid_id}/trigger-loss-analysis", response_model=BaseResponse[dict])
async def trigger_loss_analysis_task(
    bid_id: UUID,
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[dict]:
    """Trigger loss analysis as background task."""
    task = analyze_bid_loss_task.delay(str(bid_id), str(company_id))

    return BaseResponse(
        data={
            "task_id": task.id,
            "status": "queued",
            "message": "Loss analysis task queued successfully"
        },
        trace_id=trace_id
    )


@router.post("/{bid_id}/create-payment-schedule", response_model=BaseResponse[dict])
async def trigger_payment_schedule_task(
    bid_id: UUID,
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[dict]:
    """Trigger payment schedule creation as background task."""
    task = create_payment_schedule_task.delay(str(bid_id), str(company_id))

    return BaseResponse(
        data={
            "task_id": task.id,
            "status": "queued",
            "message": "Payment schedule creation task queued successfully"
        },
        trace_id=trace_id
    )


@router.post("/process-payment-follow-ups", response_model=BaseResponse[dict])
async def trigger_payment_follow_up_task(
    days_overdue: int = Query(30, ge=0),
    send_notifications: bool = Query(False),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[dict]:
    """Trigger payment follow-up processing as background task."""
    task = process_payment_follow_ups_task.delay(
        str(company_id), days_overdue, True, send_notifications
    )

    return BaseResponse(
        data={
            "task_id": task.id,
            "status": "queued",
            "message": "Payment follow-up processing task queued successfully"
        },
        trace_id=trace_id
    )
