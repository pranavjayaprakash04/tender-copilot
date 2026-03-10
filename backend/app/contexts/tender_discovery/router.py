from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

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
    get_db_session,
    get_lang_context,
    get_pagination_params,
    get_trace_id,
)
from app.shared.lang_context import LangContext
from app.shared.schemas import BaseResponse, PaginatedResponse

router = APIRouter(prefix="/tenders", tags=["tender-discovery"])


def get_tender_service(
    session = Depends(get_db_session)
) -> TenderDiscoveryService:
    """Dependency to get tender service."""
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


# Tender CRUD Operations
@router.post("", response_model=BaseResponse[TenderResponse])
async def create_tender(
    tender_data: TenderCreate,
    service: TenderDiscoveryService = Depends(get_tender_service),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderResponse]:
    """Create a new tender."""
    tender = await service.create_tender(tender_data, trace_id)
    return BaseResponse(data=tender, trace_id=trace_id)


@router.get("", response_model=PaginatedResponse[TenderResponse])
async def list_tenders(
    search_query: str | None = Query(None),
    category: TenderCategory | None = Query(None),
    min_value: float | None = Query(None),
    max_value: float | None = Query(None),
    state: str | None = Query(None),
    source: TenderSource | None = Query(None),
    status: TenderStatus | None = Query(None),
    priority: TenderPriority | None = Query(None),
    is_bookmarked: bool | None = Query(None),
    is_active: bool | None = Query(None),
    deadline_days: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    pagination: dict = Depends(get_pagination_params),
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> PaginatedResponse[TenderResponse]:
    """List tenders with filters."""
    from datetime import datetime

    filters = TenderSearchFilters(
        search_query=search_query,
        category=category,
        min_value=min_value,
        max_value=max_value,
        state=state,
        source=source,
        status=status,
        priority=priority,
        is_bookmarked=is_bookmarked,
        is_active=is_active,
        deadline_days=deadline_days,
        date_from=datetime.fromisoformat(date_from.replace('Z', '+00:00')) if date_from else None,
        date_to=datetime.fromisoformat(date_to.replace('Z', '+00:00')) if date_to else None
    )

    tenders = await service.list_tenders(
        company_id, filters, pagination["page"], pagination["page_size"], trace_id
    )

    return PaginatedResponse(
        data=tenders.tenders,
        pagination={
            "page": pagination["page"],
            "page_size": pagination["page_size"],
            "total_items": tenders.total,
            "total_pages": (tenders.total + pagination["page_size"] - 1) // pagination["page_size"],
            "has_next": pagination["page"] * pagination["page_size"] < tenders.total,
            "has_previous": pagination["page"] > 1
        },
        trace_id=trace_id
    )


@router.get("/{tender_id}", response_model=BaseResponse[TenderResponse])
async def get_tender(
    tender_id: UUID,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderResponse]:
    """Get a specific tender."""
    tender = await service.get_tender(tender_id, company_id, trace_id)
    return BaseResponse(data=tender, trace_id=trace_id)


@router.put("/{tender_id}", response_model=BaseResponse[TenderResponse])
async def update_tender(
    tender_id: UUID,
    update_data: TenderUpdate,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderResponse]:
    """Update a tender."""
    tender = await service.update_tender(tender_id, company_id, update_data, trace_id)
    return BaseResponse(data=tender, trace_id=trace_id)


@router.delete("/{tender_id}")
async def delete_tender(
    tender_id: UUID,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Delete a tender."""
    await service.delete_tender(tender_id, company_id, trace_id)
    return JSONResponse(content={"message": "Tender deleted successfully"}, status_code=200)


# Bookmark Operations
@router.post("/{tender_id}/bookmark", response_model=BaseResponse[TenderResponse])
async def toggle_bookmark(
    tender_id: UUID,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderResponse]:
    """Toggle tender bookmark status."""
    tender = await service.toggle_bookmark(tender_id, company_id, trace_id)
    return BaseResponse(data=tender, trace_id=trace_id)


@router.get("/bookmarked/list", response_model=PaginatedResponse[TenderResponse])
async def get_bookmarked_tenders(
    pagination: dict = Depends(get_pagination_params),
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> PaginatedResponse[TenderResponse]:
    """Get bookmarked tenders."""
    tenders = await service.get_bookmarked_tenders(
        company_id, pagination["page"], pagination["page_size"], trace_id
    )

    return PaginatedResponse(
        data=tenders.tenders,
        pagination={
            "page": pagination["page"],
            "page_size": pagination["page_size"],
            "total_items": tenders.total,
            "total_pages": (tenders.total + pagination["page_size"] - 1) // pagination["page_size"],
            "has_next": pagination["page"] * pagination["page_size"] < tenders.total,
            "has_previous": pagination["page"] > 1
        },
        trace_id=trace_id
    )


# Deadline and Urgent Tenders
@router.get("/closing-soon/list", response_model=BaseResponse[list[TenderResponse]])
async def get_closing_soon_tenders(
    days: int = Query(7, ge=1, le=30),
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[TenderResponse]]:
    """Get tenders closing within specified days."""
    tenders = await service.get_closing_soon_tenders(company_id, days, trace_id)
    return BaseResponse(data=tenders, trace_id=trace_id)


@router.get("/urgent/list", response_model=BaseResponse[list[TenderResponse]])
async def get_urgent_tenders(
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[TenderResponse]]:
    """Get urgent tenders (closing within 3 days)."""
    tenders = await service.get_urgent_tenders(company_id, trace_id)
    return BaseResponse(data=tenders, trace_id=trace_id)


# Statistics
@router.get("/stats/overview", response_model=BaseResponse[TenderStatsResponse])
async def get_tender_stats(
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderStatsResponse]:
    """Get tender statistics."""
    stats = await service.get_tender_stats(company_id, trace_id)
    return BaseResponse(data=stats, trace_id=trace_id)


# Classification
@router.post("/classify", response_model=BaseResponse[TenderClassificationResponse])
async def classify_tender(
    request: TenderClassificationRequest,
    service: TenderDiscoveryService = Depends(get_tender_service),
    lang: LangContext = Depends(get_lang_context),
    trace_id: str = Depends(get_trace_id),
    company_id: UUID = Depends(get_current_company_id)
) -> BaseResponse[TenderClassificationResponse]:
    """Classify a tender using AI."""
    classification = await service.classify_tender(
        request, lang, trace_id, str(company_id)
    )
    return BaseResponse(data=classification, trace_id=trace_id)


# Bulk Operations
@router.put("/bulk/update", response_model=BaseResponse[list[TenderResponse]])
async def bulk_update_tenders(
    bulk_data: TenderBulkUpdate,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[TenderResponse]]:
    """Bulk update tenders."""
    tenders = await service.bulk_update_tenders(bulk_data, company_id, trace_id)
    return BaseResponse(data=tenders, trace_id=trace_id)


@router.delete("/bulk/delete")
async def bulk_delete_tenders(
    bulk_data: TenderBulkDelete,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Bulk delete tenders."""
    await service.bulk_delete_tenders(bulk_data, company_id, trace_id)
    return JSONResponse(content={"message": f"Deleted {len(bulk_data.tender_ids)} tenders"}, status_code=200)


# Search Management
@router.post("/searches", response_model=BaseResponse[TenderSearchResponse])
async def create_search(
    search_data: TenderSearchCreate,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderSearchResponse]:
    """Create a new search."""
    search = await service.create_search(search_data, company_id, trace_id)
    return BaseResponse(data=search, trace_id=trace_id)


@router.get("/searches/list", response_model=BaseResponse[list[TenderSearchResponse]])
async def get_searches(
    saved_only: bool = Query(False),
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[TenderSearchResponse]]:
    """Get searches for a company."""
    searches = await service.get_searches(company_id, saved_only, trace_id)
    return BaseResponse(data=searches, trace_id=trace_id)


@router.put("/searches/{search_id}", response_model=BaseResponse[TenderSearchResponse])
async def update_search(
    search_id: UUID,
    update_data: TenderSearchUpdate,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderSearchResponse]:
    """Update a search."""
    search = await service.update_search(search_id, company_id, update_data, trace_id)
    return BaseResponse(data=search, trace_id=trace_id)


@router.delete("/searches/{search_id}")
async def delete_search(
    search_id: UUID,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Delete a search."""
    await service.delete_search(search_id, company_id, trace_id)
    return JSONResponse(content={"message": "Search deleted successfully"}, status_code=200)


@router.post("/searches/{search_id}/run", response_model=PaginatedResponse[TenderResponse])
async def run_saved_search(
    search_id: UUID,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> PaginatedResponse[TenderResponse]:
    """Run a saved search and return results."""
    results = await service.run_saved_search(search_id, company_id, trace_id)

    return PaginatedResponse(
        data=results.tenders,
        pagination={
            "page": 1,
            "page_size": len(results.tenders),
            "total_items": results.total,
            "total_pages": 1,
            "has_next": False,
            "has_previous": False
        },
        trace_id=trace_id
    )


# Alert Management
@router.post("/alerts", response_model=BaseResponse[TenderAlertResponse])
async def create_alert(
    alert_data: TenderAlertCreate,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderAlertResponse]:
    """Create a new alert."""
    alert = await service.create_alert(alert_data, company_id, trace_id)
    return BaseResponse(data=alert, trace_id=trace_id)


@router.get("/alerts/list", response_model=BaseResponse[list[TenderAlertResponse]])
async def get_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[list[TenderAlertResponse]]:
    """Get alerts for a company."""
    alerts = await service.get_alerts(company_id, unread_only, limit, trace_id)
    return BaseResponse(data=alerts, trace_id=trace_id)


@router.put("/alerts/{alert_id}", response_model=BaseResponse[TenderAlertResponse])
async def update_alert(
    alert_id: UUID,
    update_data: TenderAlertUpdate,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[TenderAlertResponse]:
    """Update an alert."""
    alert = await service.update_alert(alert_id, company_id, update_data, trace_id)
    return BaseResponse(data=alert, trace_id=trace_id)


@router.put("/alerts/mark-all-read")
async def mark_all_alerts_read(
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Mark all alerts as read."""
    count = await service.mark_all_alerts_read(company_id, trace_id)
    return JSONResponse(content={"message": f"Marked {count} alerts as read"}, status_code=200)


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: UUID,
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> JSONResponse:
    """Delete an alert."""
    await service.delete_alert(alert_id, company_id, trace_id)
    return JSONResponse(content={"message": "Alert deleted successfully"}, status_code=200)


@router.get("/alerts/unread-count", response_model=BaseResponse[int])
async def get_unread_alerts_count(
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[int]:
    """Get count of unread alerts."""
    count = await service.get_unread_alerts_count(company_id, trace_id)
    return BaseResponse(data=count, trace_id=trace_id)


@router.post("/alerts/create-deadline-reminders", response_model=BaseResponse[int])
async def create_deadline_alerts(
    service: TenderDiscoveryService = Depends(get_tender_service),
    company_id: UUID = Depends(get_current_company_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[int]:
    """Create deadline reminder alerts."""
    count = await service.create_deadline_alerts(company_id, trace_id)
    return BaseResponse(data=count, trace_id=trace_id)
