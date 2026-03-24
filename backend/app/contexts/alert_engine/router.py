from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.contexts.alert_engine.repository import (
    NotificationPreferenceRepository,
    NotificationRepository,
    NotificationTemplateRepository,
)
from app.contexts.alert_engine.schemas import (
    BulkNotificationCreate,
    BulkNotificationResponse,
    NotificationCreate,
    NotificationPreferenceCreate,
    NotificationPreferenceResponse,
    NotificationResponse,
    NotificationStats,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationUpdate,
)
from app.contexts.alert_engine.service import AlertEngineService
from app.dependencies import (
    get_current_company_id,
    get_current_user_id,
    get_db_session,
    get_pagination_params,
    get_trace_id,
)
from app.shared.schemas import BaseResponse, PaginatedResponse

router = APIRouter(prefix="/notifications", tags=["alert-engine"])


def get_alert_engine_service(
    session=Depends(get_db_session),
) -> AlertEngineService:
    """Dependency to get alert engine service."""
    from app.config import settings
    from app.infrastructure.resend_client import ResendClient
    from app.infrastructure.whatsapp_client import WhatsAppClient

    # Safely instantiate ResendClient — skip if API key is missing
    try:
        resend = ResendClient() if getattr(settings, "RESEND_API_KEY", None) else None
    except Exception:
        resend = None

    # Safely instantiate WhatsAppClient — skip if credentials are missing
    try:
        whatsapp = (
            WhatsAppClient()
            if (
                getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", None)
                and getattr(settings, "WHATSAPP_ACCESS_TOKEN", None)
            )
            else None
        )
    except Exception:
        whatsapp = None

    return AlertEngineService(
        notification_repo=NotificationRepository(session),
        template_repo=NotificationTemplateRepository(session),
        preference_repo=NotificationPreferenceRepository(session),
        resend_client=resend,
        whatsapp_client=whatsapp,
    )


# Notification CRUD
@router.post("", response_model=BaseResponse[NotificationResponse])
async def create_notification(
    notification_data: NotificationCreate,
    service: AlertEngineService = Depends(get_alert_engine_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> BaseResponse[NotificationResponse]:
    """Create a new notification."""
    notification = await service.create_notification(notification_data, company_id, trace_id)

    if not notification:
        return BaseResponse(
            data=None,
            message="Notification skipped due to user preferences",
            trace_id=trace_id,
        )

    return BaseResponse(data=NotificationResponse.model_validate(notification), trace_id=trace_id)


@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    notification_type: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    recipient: str | None = Query(None),
    created_from: str | None = Query(None),
    created_to: str | None = Query(None),
    has_failed: bool | None = Query(None),
    pagination: dict = Depends(get_pagination_params),
    service: AlertEngineService = Depends(get_alert_engine_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> PaginatedResponse[NotificationResponse]:
    """List notifications with filters."""
    from datetime import datetime

    filters = {}
    if notification_type:
        filters["notification_type"] = notification_type
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    if recipient:
        filters["recipient"] = recipient
    if created_from:
        filters["created_from"] = datetime.fromisoformat(created_from.replace("Z", "+00:00"))
    if created_to:
        filters["created_to"] = datetime.fromisoformat(created_to.replace("Z", "+00:00"))
    if has_failed is not None:
        filters["has_failed"] = has_failed

    notifications, total = await service.get_notifications(
        company_id, filters, pagination["page"], pagination["page_size"], trace_id
    )

    return PaginatedResponse(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        pagination={
            "page": pagination["page"],
            "page_size": pagination["page_size"],
            "total_items": total,
            "total_pages": (total + pagination["page_size"] - 1) // pagination["page_size"],
            "has_next": pagination["page"] * pagination["page_size"] < total,
            "has_previous": pagination["page"] > 1,
        },
        trace_id=trace_id,
    )


@router.get("/{notification_id}", response_model=BaseResponse[NotificationResponse])
async def get_notification(
    notification_id: UUID,
    service: AlertEngineService = Depends(get_alert_engine_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> BaseResponse[NotificationResponse]:
    """Get a specific notification."""
    notification = await service.get_notification(notification_id, company_id, trace_id)
    return BaseResponse(data=NotificationResponse.model_validate(notification), trace_id=trace_id)


@router.put("/{notification_id}", response_model=BaseResponse[NotificationResponse])
async def update_notification(
    notification_id: UUID,
    update_data: NotificationUpdate,
    service: AlertEngineService = Depends(get_alert_engine_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> BaseResponse[NotificationResponse]:
    """Update a notification."""
    notification = await service.update_notification(notification_id, company_id, update_data, trace_id)
    return BaseResponse(data=NotificationResponse.model_validate(notification), trace_id=trace_id)


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    service: AlertEngineService = Depends(get_alert_engine_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> JSONResponse:
    """Delete a notification."""
    await service.update_notification(
        notification_id,
        company_id,
        NotificationUpdate(status="deleted"),
        trace_id,
    )
    return JSONResponse(content={"message": "Notification deleted successfully"}, status_code=200)


# Statistics
@router.get("/stats/overview", response_model=BaseResponse[NotificationStats])
async def get_notification_stats(
    service: AlertEngineService = Depends(get_alert_engine_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> BaseResponse[NotificationStats]:
    """Get notification statistics."""
    stats = await service.get_notification_stats(company_id, trace_id)
    return BaseResponse(data=stats, trace_id=trace_id)


# Retry failed notifications
@router.post("/retry-failed", response_model=BaseResponse[dict])
async def retry_failed_notifications(
    service: AlertEngineService = Depends(get_alert_engine_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> BaseResponse[dict]:
    """Retry failed notifications."""
    retried = await service.retry_failed_notifications(company_id, trace_id)
    return BaseResponse(data={"retried_count": len(retried)}, trace_id=trace_id)


# Templates
@router.post("/templates", response_model=BaseResponse[NotificationTemplateResponse])
async def create_template(
    template_data: NotificationTemplateCreate,
    service: AlertEngineService = Depends(get_alert_engine_service),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> BaseResponse[NotificationTemplateResponse]:
    """Create a notification template."""
    template = await service.create_template(template_data, trace_id)
    return BaseResponse(data=NotificationTemplateResponse.model_validate(template), trace_id=trace_id)


# Preferences
@router.post("/preferences", response_model=BaseResponse[NotificationPreferenceResponse])
async def create_preference(
    preference_data: NotificationPreferenceCreate,
    service: AlertEngineService = Depends(get_alert_engine_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> BaseResponse[NotificationPreferenceResponse]:
    """Create notification preferences."""
    preference = await service.create_preference(preference_data, company_id, trace_id)
    return BaseResponse(data=NotificationPreferenceResponse.model_validate(preference), trace_id=trace_id)


# Bulk operations
@router.post("/bulk", response_model=BaseResponse[BulkNotificationResponse])
async def create_bulk_notifications(
    bulk_data: BulkNotificationCreate,
    service: AlertEngineService = Depends(get_alert_engine_service),
    company_id: UUID = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> BaseResponse[BulkNotificationResponse]:
    """Create multiple notifications."""
    created = []
    failed = []

    for notification_data in bulk_data.notifications:
        try:
            notification = await service.create_notification(notification_data, company_id, trace_id)
            if notification:
                created.append(NotificationResponse.model_validate(notification))
        except Exception as e:
            failed.append({"error": str(e), "notification": notification_data.model_dump()})

    response = BulkNotificationResponse(
        created=created,
        failed=failed,
        total_requested=len(bulk_data.notifications),
        total_created=len(created),
        total_failed=len(failed),
    )

    return BaseResponse(data=response, trace_id=trace_id)
