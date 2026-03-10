"""Alert Engine Context.

Handles notifications, alerts, and cross-context communication via domain events.
"""

from .models import (
    Notification,
    NotificationPreference,
    NotificationPriority,
    NotificationStatus,
    NotificationTemplate,
    NotificationType,
)
from .repository import (
    NotificationPreferenceRepository,
    NotificationRepository,
    NotificationTemplateRepository,
)
from .router import router
from .schemas import (
    AlertEvent,
    BulkNotificationCreate,
    BulkNotificationResponse,
    NotificationCreate,
    NotificationDeliveryReport,
    NotificationPreferenceCreate,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    NotificationSearchFilters,
    NotificationStats,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
    NotificationUpdate,
)
from .service import AlertEngineService
from .tasks import (
    celery_app,
    cleanup_old_notifications_task,
    process_domain_events_task,
    retry_failed_notifications_task,
    send_daily_digest_task,
)

__all__ = [
    "Notification",
    "NotificationTemplate",
    "NotificationPreference",
    "NotificationType",
    "NotificationStatus",
    "NotificationPriority",
    "NotificationResponse",
    "NotificationCreate",
    "NotificationUpdate",
    "NotificationTemplateResponse",
    "NotificationTemplateCreate",
    "NotificationTemplateUpdate",
    "NotificationPreferenceResponse",
    "NotificationPreferenceCreate",
    "NotificationPreferenceUpdate",
    "NotificationSearchFilters",
    "NotificationStats",
    "BulkNotificationCreate",
    "BulkNotificationResponse",
    "AlertEvent",
    "NotificationDeliveryReport",
    "AlertEngineService",
    "NotificationRepository",
    "NotificationTemplateRepository",
    "NotificationPreferenceRepository",
    "router",
    "celery_app",
    "process_domain_events_task",
    "retry_failed_notifications_task",
    "cleanup_old_notifications_task",
    "send_daily_digest_task",
]
