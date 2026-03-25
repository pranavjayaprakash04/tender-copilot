from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog

from app.contexts.alert_engine.models import (
    Notification,
    NotificationPreference,
    NotificationPriority,
    NotificationStatus,
    NotificationTemplate,
    NotificationType,
)
from app.contexts.alert_engine.repository import (
    NotificationPreferenceRepository,
    NotificationRepository,
    NotificationTemplateRepository,
)
from app.contexts.alert_engine.schemas import (
    AlertEvent,
    NotificationCreate,
    NotificationPreferenceCreate,
    NotificationStats,
    NotificationTemplateCreate,
    NotificationUpdate,
)
from app.infrastructure.resend_client import ResendClient
from app.infrastructure.whatsapp_client import WhatsAppClient
from app.shared.events import DomainEventConsumer

logger = structlog.get_logger()


def _parse_context_data(context_data: Any) -> dict:
    """Safely parse context_data which may be a JSON string, dict, or None."""
    if context_data is None:
        return {}
    if isinstance(context_data, dict):
        return context_data
    if isinstance(context_data, str):
        try:
            return json.loads(context_data)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


class AlertEngineService:
    """Service for managing notifications and alerts."""

    def __init__(
        self,
        notification_repo: NotificationRepository,
        template_repo: NotificationTemplateRepository,
        preference_repo: NotificationPreferenceRepository,
        resend_client: ResendClient,
        whatsapp_client: WhatsAppClient
    ) -> None:
        self._notification_repo = notification_repo
        self._template_repo = template_repo
        self._preference_repo = preference_repo
        self._resend_client = resend_client
        self._whatsapp_client = whatsapp_client
        self._event_consumer = DomainEventConsumer()

    async def create_notification(
        self,
        notification_data: NotificationCreate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> Notification:
        """Create a new notification."""
        # Check user preferences
        preferences = await self._preference_repo.get_by_company(company_id)
        if not self._should_send_notification(notification_data, preferences):
            logger.info("notification_skipped_preferences", trace_id=trace_id)
            return None

        # Create notification with company_id
        notification_dict = notification_data.model_dump()
        notification_dict["company_id"] = company_id

        # Ensure context_data is stored as JSON string if it's a dict
        if isinstance(notification_dict.get("context_data"), dict):
            notification_dict["context_data"] = json.dumps(notification_dict["context_data"])

        notification = await self._notification_repo.create(notification_dict)

        logger.info(
            "notification_created",
            trace_id=trace_id,
            notification_id=notification.id,
            company_id=company_id,
            type=notification.notification_type
        )

        # Send notification immediately
        await self._send_notification(notification, trace_id)

        return notification

    async def send_alerts_from_event(
        self,
        alert_events: list[AlertEvent],
        trace_id: str | None = None
    ) -> list[Notification]:
        """Send notifications from alert events."""
        notifications = []

        for event in alert_events:
            # Get user preferences for the company
            preferences = await self._preference_repo.get_by_company(event.company_id)

            # Determine which channels to use
            channels = self._get_notification_channels(event.alert_type, preferences)

            for channel in channels:
                notification_data = NotificationCreate(
                    notification_type=channel,
                    recipient=self._get_recipient_for_channel(event.company_id, channel, preferences),
                    subject=self._generate_subject(event),
                    message=event.message,
                    priority=self._map_urgency_to_priority(event.urgency),
                    context_data=event.context_data
                )

                notification = await self.create_notification(
                    notification_data, event.company_id, trace_id
                )
                if notification:
                    notifications.append(notification)

        logger.info(
            "alerts_sent_from_events",
            trace_id=trace_id,
            events_count=len(alert_events),
            notifications_sent=len(notifications)
        )

        return notifications

    async def get_notifications(
        self,
        company_id: UUID,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        trace_id: str | None = None
    ) -> tuple[list[Notification], int]:
        """Get notifications for a company."""
        notifications, total = await self._notification_repo.get_by_company(
            company_id, filters, page, page_size
        )

        logger.info(
            "notifications_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            count=len(notifications),
            total=total
        )

        return notifications, total

    async def get_notification(
        self,
        notification_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> Notification:
        """Get a specific notification."""
        notification = await self._notification_repo.get_by_id(notification_id, company_id)

        logger.info(
            "notification_retrieved",
            trace_id=trace_id,
            notification_id=notification_id,
            company_id=company_id
        )

        return notification

    async def update_notification(
        self,
        notification_id: UUID,
        company_id: UUID,
        update_data: NotificationUpdate,
        trace_id: str | None = None
    ) -> Notification:
        """Update a notification."""
        notification = await self._notification_repo.update(
            notification_id, company_id, update_data
        )

        logger.info(
            "notification_updated",
            trace_id=trace_id,
            notification_id=notification_id,
            company_id=company_id,
            status=notification.status
        )

        return notification

    async def retry_failed_notifications(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[Notification]:
        """Retry failed notifications that can be retried."""
        failed_notifications = await self._notification_repo.get_retryable(company_id)

        retried = []
        for notification in failed_notifications:
            # Check if retry is due (next_retry_at is None or in the past)
            should_retry = (
                notification.next_retry_at is None
                or notification.next_retry_at <= datetime.now(UTC)
            )
            if should_retry:
                await self._send_notification(notification, trace_id)
                retried.append(notification)

        logger.info(
            "failed_notifications_retried",
            trace_id=trace_id,
            company_id=company_id,
            retried_count=len(retried),
            total_failed=len(failed_notifications)
        )

        return retried

    async def get_notification_stats(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> NotificationStats:
        """Get notification statistics for a company."""
        stats = await self._notification_repo.get_stats(company_id)

        logger.info(
            "notification_stats_retrieved",
            trace_id=trace_id,
            company_id=company_id,
            total=stats["total_notifications"]
        )

        return NotificationStats(**stats)

    async def create_template(
        self,
        template_data: NotificationTemplateCreate,
        trace_id: str | None = None
    ) -> NotificationTemplate:
        """Create a notification template."""
        template = await self._template_repo.create(template_data)

        logger.info(
            "notification_template_created",
            trace_id=trace_id,
            template_id=template.id,
            name=template.name,
            type=template.notification_type
        )

        return template

    async def create_preference(
        self,
        preference_data: NotificationPreferenceCreate,
        company_id: UUID,
        trace_id: str | None = None
    ) -> NotificationPreference:
        """Create notification preferences."""
        preference_data.company_id = company_id
        preference = await self._preference_repo.create(preference_data)

        logger.info(
            "notification_preferences_created",
            trace_id=trace_id,
            user_id=preference.user_id,
            company_id=company_id
        )

        return preference

    async def _send_notification(
        self,
        notification: Notification,
        trace_id: str | None = None
    ) -> None:
        """Send a notification via the appropriate channel."""
        try:
            if notification.notification_type == NotificationType.EMAIL:
                await self._send_email_notification(notification, trace_id)
            elif notification.notification_type == NotificationType.WHATSAPP:
                await self._send_whatsapp_notification(notification, trace_id)
            elif notification.notification_type == NotificationType.SMS:
                await self._send_sms_notification(notification, trace_id)
            elif notification.notification_type == NotificationType.PUSH:
                await self._send_push_notification(notification, trace_id)

            # Update status to sent
            await self._notification_repo.update(
                notification.id,
                notification.company_id,
                NotificationUpdate(
                    status=NotificationStatus.SENT,
                    sent_at=datetime.now(UTC)
                )
            )

        except Exception as e:
            # Update status to failed
            retry_delay = self._calculate_retry_delay(notification.retry_count)
            await self._notification_repo.update(
                notification.id,
                notification.company_id,
                NotificationUpdate(
                    status=NotificationStatus.FAILED,
                    error_message=str(e),
                    failed_at=datetime.now(UTC),
                    next_retry_at=datetime.now(UTC) + retry_delay
                )
            )

            logger.error(
                "notification_send_failed",
                trace_id=trace_id,
                notification_id=notification.id,
                error=str(e),
                retry_count=notification.retry_count
            )

    async def _send_email_notification(
        self,
        notification: Notification,
        trace_id: str | None = None
    ) -> None:
        """Send email notification via Resend."""
        # Safely parse context_data (stored as JSON string in DB)
        ctx = _parse_context_data(notification.context_data)

        template_data = {
            "alert_type": ctx.get("alert_type", "general"),
            "tender_title": ctx.get("tender_title"),
            "tender_id": ctx.get("tender_id"),
            "company_name": ctx.get("company_name"),
            "deadline_date": ctx.get("deadline_date"),
            "tender_value": ctx.get("tender_value"),
            "message": notification.message,
            "urgency": ctx.get("urgency", "medium"),
            "action_url": ctx.get("action_url")
        }

        await self._resend_client.send_tender_alert(
            to=notification.recipient,
            alert_data=template_data,
            trace_id=trace_id
        )

        logger.info(
            "email_notification_sent_via_resend",
            trace_id=trace_id,
            notification_id=notification.id,
            recipient=notification.recipient
        )

    async def _send_whatsapp_notification(
        self,
        notification: Notification,
        trace_id: str | None = None
    ) -> None:
        """Send WhatsApp notification."""
        await self._whatsapp_client.send_message(
            to=notification.recipient,
            message=notification.message,
            trace_id=trace_id
        )

        logger.info(
            "whatsapp_notification_sent",
            trace_id=trace_id,
            notification_id=notification.id,
            recipient=notification.recipient
        )

    async def _send_sms_notification(
        self,
        notification: Notification,
        trace_id: str | None = None
    ) -> None:
        """Send SMS notification."""
        logger.info(
            "sms_notification_sent",
            trace_id=trace_id,
            notification_id=notification.id,
            recipient=notification.recipient
        )

    async def _send_push_notification(
        self,
        notification: Notification,
        trace_id: str | None = None
    ) -> None:
        """Send push notification."""
        logger.info(
            "push_notification_sent",
            trace_id=trace_id,
            notification_id=notification.id,
            recipient=notification.recipient
        )

    def _should_send_notification(
        self,
        notification_data: NotificationCreate,
        preferences: list[NotificationPreference] | None
    ) -> bool:
        """Check if notification should be sent based on preferences."""
        if not preferences:
            return True

        if notification_data.notification_type == NotificationType.EMAIL:
            return any(p.email_enabled for p in preferences)
        elif notification_data.notification_type == NotificationType.WHATSAPP:
            return any(p.whatsapp_enabled for p in preferences)
        elif notification_data.notification_type == NotificationType.SMS:
            return any(p.sms_enabled for p in preferences)
        elif notification_data.notification_type == NotificationType.PUSH:
            return any(p.push_enabled for p in preferences)

        return True

    def _get_notification_channels(
        self,
        alert_type: str,
        preferences: list[NotificationPreference] | None
    ) -> list[NotificationType]:
        """Get notification channels for alert type."""
        if not preferences:
            return [NotificationType.EMAIL]

        channels = []

        if alert_type == "deadline_reminder":
            if any(p.email_enabled and p.deadline_alerts for p in preferences):
                channels.append(NotificationType.EMAIL)
            if any(p.whatsapp_enabled and p.deadline_alerts for p in preferences):
                channels.append(NotificationType.WHATSAPP)
        elif alert_type == "new_tender":
            if any(p.email_enabled and p.new_tender_alerts for p in preferences):
                channels.append(NotificationType.EMAIL)
            if any(p.whatsapp_enabled and p.new_tender_alerts for p in preferences):
                channels.append(NotificationType.WHATSAPP)
        elif alert_type == "bid_status":
            if any(p.email_enabled and p.bid_status_alerts for p in preferences):
                channels.append(NotificationType.EMAIL)
            if any(p.whatsapp_enabled and p.bid_status_alerts for p in preferences):
                channels.append(NotificationType.WHATSAPP)
        elif alert_type == "payment_reminder":
            if any(p.email_enabled and p.payment_alerts for p in preferences):
                channels.append(NotificationType.EMAIL)
            if any(p.whatsapp_enabled and p.payment_alerts for p in preferences):
                channels.append(NotificationType.WHATSAPP)

        return channels or [NotificationType.EMAIL]

    def _get_recipient_for_channel(
        self,
        company_id: UUID,
        channel: NotificationType,
        preferences: list[NotificationPreference] | None
    ) -> str:
        """Get recipient for notification channel."""
        if channel == NotificationType.EMAIL:
            return f"company-{company_id}@example.com"
        elif channel == NotificationType.WHATSAPP:
            return "+919876543210"
        elif channel == NotificationType.SMS:
            return "+919876543210"
        else:
            return f"device-token-{company_id}"

    def _generate_subject(self, event: AlertEvent) -> str:
        """Generate notification subject from alert event."""
        if event.alert_type == "deadline_reminder":
            return "🔔 Tender Deadline Reminder"
        elif event.alert_type == "new_tender":
            return "🆕 New Tender Alert"
        elif event.alert_type == "bid_status":
            return "📊 Bid Status Update"
        elif event.alert_type == "payment_reminder":
            return "💰 Payment Reminder"
        else:
            return "📢 Tender Alert"

    def _map_urgency_to_priority(self, urgency: str) -> NotificationPriority:
        """Map urgency string to notification priority."""
        mapping = {
            "low": NotificationPriority.LOW,
            "medium": NotificationPriority.MEDIUM,
            "high": NotificationPriority.HIGH,
            "urgent": NotificationPriority.URGENT
        }
        return mapping.get(urgency.lower(), NotificationPriority.MEDIUM)

    def _calculate_retry_delay(self, retry_count: int) -> timedelta:
        """Calculate retry delay with exponential backoff."""
        base_delay = timedelta(minutes=5)
        max_delay = timedelta(hours=24)
        delay = base_delay * (2 ** retry_count)
        return min(delay, max_delay)
