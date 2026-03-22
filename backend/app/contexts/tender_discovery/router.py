from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.contexts.tender_discovery.models import (
    TenderCategory,
    TenderPriority,
    TenderSource,
    TenderStatus,
)
from app.contexts.tender_discovery.schemas import (
    TenderAlertCreate,
    TenderAlertResponse,
    TenderAlertUpdate,
    TenderBulkDelete,
    TenderBulkUpdate,
    TenderClassificationRequest,
    TenderClassificationResponse,
    TenderCreate,
    TenderResponse,
    TenderSearchCreate,
    TenderSearchFilters,
    TenderSearchResponse,
    TenderSearchUpdate,
    TenderStatsResponse,
    TenderUpdate,
)
from app.contexts.tender_discovery.service import TenderDiscoveryService
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

router = APIRouter(prefix="/tenders", tags=["tender-discovery"])


def get_tender_service(
    session=Depends(get_db_session)
) -> TenderDiscoveryService:
    from app.contexts.tender_discovery.repository import (
        TenderAlertRepository,
        TenderRepository,
        TenderSearchRepository,
    )
    from app.infrastructure.groq_client import GroqClient

    return TenderDiscoveryService(
        tender_repo=TenderRepository(session),
        search_repo=TenderSearchRepository(session),
        alert_repo=TenderAlertRepository(session),
        groq_client=GroqClient()
    )


# ── Main list endpoint — queries real scraper schema directly ──────────────────
@router.get("")
async def list_tenders(
    search: str | None = Query(None),
    category: str | None = Query(None),
    state: str | None = Query(None),
    deadline: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session=Depends(get_db_session),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
):
    """List tenders from the real scraper table."""
    conditions = ["1=1"]
    params: dict = {}

    if search:
        conditions.append("(title ILIKE :search OR organization ILIKE :search)")
        params["search"] = f"%{search}%"

    if category:
        conditions.append("category ILIKE :category")
        params["category"] = f"%{category}%"

    if state:
        conditions.append("location ILIKE :state")
        params["state"] = f"%{state}%"

    if deadline:
        try:
            days = int(deadline)
            conditions.append("bid_end_date <= CURRENT_DATE + :days * INTERVAL '1 day'")
            params["days"] = days
        except ValueError:
            pass

    where = " AND ".join(conditions)
    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    count_result = await session.execute(
        text(f"SELECT COUNT(*) FROM tenders WHERE {where}"),
        params
    )
    total = count_result.scalar()

    rows = await session.execute(
        text(f"""
            SELECT
                id::text AS id,
                tender_id,
                title,
                organization,
                portal AS source,
                detail_url AS source_url,
                category,
                status,
                location AS state,
                bid_end_date::text AS deadline,
                estimated_value::text AS value,
                emd_amount::text AS emd_amount,
                scraped_at::text AS posted_date,
                apply_url,
                required_documents,
                details
            FROM tenders
            WHERE {where}
            ORDER BY scraped_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params
    )

    tenders = [dict(row._mapping) for row in rows]

    return {
        "tenders": tenders,
        "total": total,
        "page": page,
        "limit": limit
    }


# ── All other endpoints unchanged ─────────────────────────────────────────────

@router.post("/create", response_model=BaseResponse[TenderResponse])
async def create_tender(
    tender_data: TenderCreate,
    service: TenderDiscoveryService = Depends(get_tender_service),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderResponse]:
    tender = await service.create_tender(tender_data, trace_id)
    return BaseResponse(data=tender, trace_id=trace_id)


@router.get("/{tender_id}", response_model=BaseResponse[TenderResponse])
async def get_tender(
    tender_id: UUID,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderResponse]:
    tender = await service.get_tender(tender_id, company_id, trace_id)
    return BaseResponse(data=tender, trace_id=trace_id)


@router.get("/stats/overview", response_model=BaseResponse[TenderStatsResponse])
async def get_tender_stats(
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderStatsResponse]:
    stats = await service.get_tender_stats(company_id, trace_id)
    return BaseResponse(data=stats, trace_id=trace_id)


@router.get("/closing-soon/list", response_model=BaseResponse[list[TenderResponse]])
async def get_closing_soon_tenders(
    days: int = Query(7, ge=1, le=30),
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[TenderResponse]]:
    tenders = await service.get_closing_soon_tenders(company_id, days, trace_id)
    return BaseResponse(data=tenders, trace_id=trace_id)


@router.get("/alerts/list", response_model=BaseResponse[list[TenderAlertResponse]])
async def get_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[TenderAlertResponse]]:
    alerts = await service.get_alerts(company_id, unread_only, limit, trace_id)
    return BaseResponse(data=alerts, trace_id=trace_id)
