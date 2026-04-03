from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import UUID as SQLAlchemyUUID
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class NotificationType(StrEnum):
    """Notification types."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(StrEnum):
    """Notification status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class NotificationPriority(StrEnum):
    """Notification priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """Notification model for alert engine."""
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Notification details
    notification_type: Mapped[NotificationType] = mapped_column(String(20), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)  # Email, phone, or device token
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Status and tracking
    status: Mapped[NotificationStatus] = mapped_column(String(20), nullable=False, default=NotificationStatus.PENDING)
    priority: Mapped[NotificationPriority] = mapped_column(String(20), nullable=False, default=NotificationPriority.MEDIUM)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Context data
    context_data: Mapped[dict[str, Any] | None] = mapped_column(Text, nullable=True)  # JSON string
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Response tracking
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"Notification(id={self.id}, type={self.notification_type}, status={self.status})"

    @property
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return self.retry_count < self.max_retries and self.status == NotificationStatus.FAILED

    @property
    def is_final_status(self) -> bool:
        """Check if status is final."""
        return self.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED]

    @property
    def should_retry_now(self) -> bool:
        """Check if notification should be retried now."""
        if not self.can_retry:
            return False
        if self.next_retry_at is None:
            return True
        return datetime.utcnow() >= self.next_retry_at


class NotificationTemplate(Base):
    """Notification templates."""
    __tablename__ = "notification_templates"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    notification_type: Mapped[NotificationType] = mapped_column(String(20), nullable=False)
    subject_template: Mapped[str] = mapped_column(String(500), nullable=False)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict[str, Any] | None] = mapped_column(Text, nullable=True)  # JSON string

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"NotificationTemplate(id={self.id}, name={self.name}, type={self.notification_type})"


class NotificationPreference(Base):
    """User notification preferences."""
    __tablename__ = "notification_preferences"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    user_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Notification type preferences
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Alert type preferences
    deadline_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    new_tender_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    bid_status_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    payment_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Timing preferences
    quiet_hours_start: Mapped[int] = mapped_column(Integer, nullable=True)  # Hour in 24h format
    quiet_hours_end: Mapped[int] = mapped_column(Integer, nullable=True)    # Hour in 24h format
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"NotificationPreference(id={self.id}, user_id={self.user_id})"

    def is_quiet_hours(self, current_time: datetime) -> bool:
        """Check if current time is within quiet hours."""
        if self.quiet_hours_start is None or self.quiet_hours_end is None:
            return False

        current_hour = current_time.hour

        if self.quiet_hours_start <= self.quiet_hours_end:
            # Same day range (e.g., 22:00 to 06:00)
            return self.quiet_hours_start <= current_hour <= self.quiet_hours_end
        else:
            # Overnight range (e.g., 22:00 to 06:00 next day)
            return current_hour >= self.quiet_hours_start or current_hour <= self.quiet_hours_end
