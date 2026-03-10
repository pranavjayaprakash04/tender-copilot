from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.contexts.alert_engine.models import (
    Notification,
    NotificationPreference,
    NotificationStatus,
    NotificationTemplate,
    NotificationType,
)
from app.shared.exceptions import NotFoundException

logger = structlog.get_logger()


class NotificationRepository:
    """Repository for Notification model."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def create(self, notification_data: Any) -> Notification:
        """Create a new notification."""
        notification = Notification(**notification_data.model_dump())
        self._session.add(notification)
        await self._session.commit()
        await self._session.refresh(notification)
        return notification

    async def get_by_id(self, notification_id: UUID, company_id: UUID) -> Notification:
        """Get notification by ID."""
        notification = await self._session.get(Notification, notification_id)

        if not notification or notification.company_id != company_id:
            raise NotFoundException("Notification not found")

        return notification

    async def get_by_company(
        self,
        company_id: UUID,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[list[Notification], int]:
        """Get notifications for a company with filters."""
        query = select(Notification).where(Notification.company_id == company_id)

        if filters:
            if filters.get("notification_type"):
                query = query.where(Notification.notification_type == filters["notification_type"])
            if filters.get("status"):
                query = query.where(Notification.status == filters["status"])
            if filters.get("priority"):
                query = query.where(Notification.priority == filters["priority"])
            if filters.get("recipient"):
                query = query.where(Notification.recipient.ilike(f"%{filters['recipient']}%"))
            if filters.get("created_from"):
                query = query.where(Notification.created_at >= filters["created_from"])
            if filters.get("created_to"):
                query = query.where(Notification.created_at <= filters["created_to"])
            if filters.get("has_failed"):
                query = query.where(Notification.status == NotificationStatus.FAILED)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self._session.scalar(count_query)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size)

        notifications = await self._session.execute(query)
        return list(notifications.scalars().all()), total or 0

    async def update(self, notification_id: UUID, company_id: UUID, update_data: Any) -> Notification:
        """Update a notification."""
        notification = await self.get_by_id(notification_id, company_id)

        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(notification, field, value)

        notification.updated_at = datetime.utcnow()
        await self._session.commit()
        await self._session.refresh(notification)
        return notification

    async def delete(self, notification_id: UUID, company_id: UUID) -> None:
        """Delete a notification."""
        notification = await self.get_by_id(notification_id, company_id)
        await self._session.delete(notification)
        await self._session.commit()

    async def get_retryable(self, company_id: UUID) -> list[Notification]:
        """Get notifications that can be retried."""
        query = select(Notification).where(
            and_(
                Notification.company_id == company_id,
                Notification.status == NotificationStatus.FAILED,
                Notification.retry_count < Notification.max_retries,
                or_(
                    Notification.next_retry_at.is_(None),
                    Notification.next_retry_at <= datetime.utcnow()
                )
            )
        )

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_stats(self, company_id: UUID) -> dict[str, Any]:
        """Get notification statistics for a company."""
        # Basic counts
        total_query = select(func.count(Notification.id)).where(Notification.company_id == company_id)
        total = await self._session.scalar(total_query) or 0

        sent_query = select(func.count(Notification.id)).where(
            and_(
                Notification.company_id == company_id,
                Notification.status == NotificationStatus.SENT
            )
        )
        sent = await self._session.scalar(sent_query) or 0

        failed_query = select(func.count(Notification.id)).where(
            and_(
                Notification.company_id == company_id,
                Notification.status == NotificationStatus.FAILED
            )
        )
        failed = await self._session.scalar(failed_query) or 0

        pending_query = select(func.count(Notification.id)).where(
            and_(
                Notification.company_id == company_id,
                Notification.status == NotificationStatus.PENDING
            )
        )
        pending = await self._session.scalar(pending_query) or 0

        # By type
        type_query = select(
            Notification.notification_type,
            func.count(Notification.id)
        ).where(Notification.company_id == company_id).group_by(Notification.notification_type)

        type_result = await self._session.execute(type_query)
        notifications_by_type = {row[0]: row[1] for row in type_result}

        # By priority
        priority_query = select(
            Notification.priority,
            func.count(Notification.id)
        ).where(Notification.company_id == company_id).group_by(Notification.priority)

        priority_result = await self._session.execute(priority_query)
        notifications_by_priority = {row[0]: row[1] for row in priority_result}

        # Recent failures
        recent_failures_query = select(Notification).where(
            and_(
                Notification.company_id == company_id,
                Notification.status == NotificationStatus.FAILED,
                Notification.failed_at >= datetime.utcnow() - timedelta(days=7)
            )
        ).order_by(Notification.failed_at.desc()).limit(5)

        recent_failures_result = await self._session.execute(recent_failures_query)
        recent_failures = list(recent_failures_result.scalars().all())

        return {
            "total_notifications": total,
            "sent_notifications": sent,
            "failed_notifications": failed,
            "pending_notifications": pending,
            "delivery_rate": (sent / total * 100) if total > 0 else 0,
            "failure_rate": (failed / total * 100) if total > 0 else 0,
            "notifications_by_type": notifications_by_type,
            "notifications_by_priority": notifications_by_priority,
            "recent_failures": recent_failures
        }

    async def delete_old_notifications(self, cutoff_date: datetime) -> int:
        """Delete notifications older than cutoff date."""
        query = select(Notification).where(Notification.created_at < cutoff_date)
        result = await self._session.execute(query)
        notifications = list(result.scalars().all())

        for notification in notifications:
            await self._session.delete(notification)

        await self._session.commit()
        return len(notifications)


class NotificationTemplateRepository:
    """Repository for NotificationTemplate model."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def create(self, template_data: Any) -> NotificationTemplate:
        """Create a new notification template."""
        template = NotificationTemplate(**template_data.model_dump())
        self._session.add(template)
        await self._session.commit()
        await self._session.refresh(template)
        return template

    async def get_by_id(self, template_id: UUID) -> NotificationTemplate:
        """Get template by ID."""
        template = await self._session.get(NotificationTemplate, template_id)

        if not template:
            raise NotFoundException("Template not found")

        return template

    async def get_by_name(self, name: str) -> NotificationTemplate:
        """Get template by name."""
        query = select(NotificationTemplate).where(NotificationTemplate.name == name)
        result = await self._session.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            raise NotFoundException("Template not found")

        return template

    async def get_by_type(self, notification_type: NotificationType) -> list[NotificationTemplate]:
        """Get templates by notification type."""
        query = select(NotificationTemplate).where(
            and_(
                NotificationTemplate.notification_type == notification_type,
                NotificationTemplate.is_active
            )
        )

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update(self, template_id: UUID, update_data: Any) -> NotificationTemplate:
        """Update a template."""
        template = await self.get_by_id(template_id)

        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(template, field, value)

        template.updated_at = datetime.utcnow()
        await self._session.commit()
        await self._session.refresh(template)
        return template

    async def delete(self, template_id: UUID) -> None:
        """Delete a template."""
        template = await self.get_by_id(template_id)
        await self._session.delete(template)
        await self._session.commit()


class NotificationPreferenceRepository:
    """Repository for NotificationPreference model."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def create(self, preference_data: Any) -> NotificationPreference:
        """Create new notification preferences."""
        preference = NotificationPreference(**preference_data.model_dump())
        self._session.add(preference)
        await self._session.commit()
        await self._session.refresh(preference)
        return preference

    async def get_by_user(self, user_id: UUID, company_id: UUID) -> NotificationPreference:
        """Get preferences for a user."""
        query = select(NotificationPreference).where(
            and_(
                NotificationPreference.user_id == user_id,
                NotificationPreference.company_id == company_id
            )
        )

        result = await self._session.execute(query)
        preference = result.scalar_one_or_none()

        if not preference:
            raise NotFoundException("Preferences not found")

        return preference

    async def get_by_company(self, company_id: UUID) -> list[NotificationPreference]:
        """Get all preferences for a company."""
        query = select(NotificationPreference).where(NotificationPreference.company_id == company_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update(self, user_id: UUID, company_id: UUID, update_data: Any) -> NotificationPreference:
        """Update preferences."""
        preference = await self.get_by_user(user_id, company_id)

        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(preference, field, value)

        preference.updated_at = datetime.utcnow()
        await self._session.commit()
        await self._session.refresh(preference)
        return preference

    async def delete(self, user_id: UUID, company_id: UUID) -> None:
        """Delete preferences."""
        preference = await self.get_by_user(user_id, company_id)
        await self._session.delete(preference)
        await self._session.commit()
