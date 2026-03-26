from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.contexts.alert_engine.models import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)


class NotificationCreate(BaseModel):
    """Create notification request."""
    notification_type: NotificationType
    recipient: str
    subject: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    context_data: dict[str, Any] | None = None
    template_id: str | None = None
    max_retries: int = 3

    model_config = ConfigDict(from_attributes=True)


class NotificationUpdate(BaseModel):
    """Update notification request."""
    status: NotificationStatus | None = None
    response: str | None = None
    error_message: str | None = None
    sent_at: datetime | None = None        # was missing — service.py sets this
    failed_at: datetime | None = None      # was missing — service.py sets this
    next_retry_at: datetime | None = None
    retry_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    """Notification response."""
    id: UUID
    company_id: UUID
    notification_type: NotificationType
    recipient: str
    subject: str
    message: str
    status: NotificationStatus
    priority: NotificationPriority
    retry_count: int
    max_retries: int
    context_data: dict[str, Any] | None
    template_id: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    next_retry_at: datetime | None
    response: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('context_data', mode='before')
    @classmethod
    def parse_context_data(cls, v):
        """Parse JSON context data."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v


class NotificationTemplateCreate(BaseModel):
    """Create notification template."""
    name: str
    notification_type: NotificationType
    subject_template: str
    message_template: str
    variables: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationTemplateUpdate(BaseModel):
    """Update notification template."""
    subject_template: str | None = None
    message_template: str | None = None
    variables: dict[str, Any] | None = None
    is_active: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationTemplateResponse(BaseModel):
    """Notification template response."""
    id: UUID
    name: str
    notification_type: NotificationType
    subject_template: str
    message_template: str
    variables: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('variables', mode='before')
    @classmethod
    def parse_variables(cls, v):
        """Parse JSON variables."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v


class NotificationPreferenceCreate(BaseModel):
    """Create notification preferences."""
    user_id: UUID
    email_enabled: bool = True
    whatsapp_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    deadline_alerts: bool = True
    new_tender_alerts: bool = True
    bid_status_alerts: bool = True
    payment_alerts: bool = True
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
    timezone: str = "UTC"

    @field_validator('quiet_hours_start', 'quiet_hours_end')
    @classmethod
    def validate_hours(cls, v):
        if v is not None and (v < 0 or v > 23):
            raise ValueError('Hour must be between 0 and 23')
        return v

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    """Update notification preferences."""
    email_enabled: bool | None = None
    whatsapp_enabled: bool | None = None
    sms_enabled: bool | None = None
    push_enabled: bool | None = None
    deadline_alerts: bool | None = None
    new_tender_alerts: bool | None = None
    bid_status_alerts: bool | None = None
    payment_alerts: bool | None = None
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
    timezone: str | None = None

    @field_validator('quiet_hours_start', 'quiet_hours_end')
    @classmethod
    def validate_hours(cls, v):
        if v is not None and (v < 0 or v > 23):
            raise ValueError('Hour must be between 0 and 23')
        return v

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceResponse(BaseModel):
    """Notification preference response."""
    id: UUID
    user_id: UUID
    company_id: UUID
    email_enabled: bool
    whatsapp_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    deadline_alerts: bool
    new_tender_alerts: bool
    bid_status_alerts: bool
    payment_alerts: bool
    quiet_hours_start: int | None
    quiet_hours_end: int | None
    timezone: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationSearchFilters(BaseModel):
    """Notification search filters."""
    notification_type: NotificationType | None = None
    status: NotificationStatus | None = None
    priority: NotificationPriority | None = None
    recipient: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    has_failed: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationStats(BaseModel):
    """Notification statistics."""
    total_notifications: int
    sent_notifications: int
    failed_notifications: int
    pending_notifications: int
    delivery_rate: float
    failure_rate: float
    notifications_by_type: dict[str, int]
    notifications_by_priority: dict[str, int]
    recent_failures: list[NotificationResponse]

    model_config = ConfigDict(from_attributes=True)


class BulkNotificationCreate(BaseModel):
    """Bulk notification creation."""
    notifications: list[NotificationCreate]

    model_config = ConfigDict(from_attributes=True)


class BulkNotificationResponse(BaseModel):
    """Bulk notification response."""
    created: list[NotificationResponse]
    failed: list[dict[str, Any]]
    total_requested: int
    total_created: int
    total_failed: int

    model_config = ConfigDict(from_attributes=True)


class AlertEvent(BaseModel):
    """Alert event from other contexts."""
    company_id: UUID
    alert_type: str
    tender_id: UUID | None = None
    bid_id: UUID | None = None
    message: str
    urgency: str = "medium"
    context_data: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationDeliveryReport(BaseModel):
    """Notification delivery report."""
    notification_id: UUID
    delivery_status: str
    delivered_at: datetime | None
    response_data: dict[str, Any] | None = None
    error_details: str | None = None

    model_config = ConfigDict(from_attributes=True)
