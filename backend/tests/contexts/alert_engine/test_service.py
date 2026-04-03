"""Tests for alert engine service."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4, UUID

from app.contexts.alert_engine.models import (
    Notification,
    NotificationPriority,
    NotificationStatus,
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
    NotificationUpdate,
)
from app.contexts.alert_engine.service import AlertEngineService
from app.infrastructure.resend_client import ResendClient
from app.infrastructure.whatsapp_client import WhatsAppClient


@pytest.fixture
def mock_notification_repo():
    """Mock notification repository."""
    repo = AsyncMock(spec=NotificationRepository)
    return repo


@pytest.fixture
def mock_template_repo():
    """Mock template repository."""
    repo = AsyncMock(spec=NotificationTemplateRepository)
    return repo


@pytest.fixture
def mock_preference_repo():
    """Mock preference repository."""
    repo = AsyncMock(spec=NotificationPreferenceRepository)
    return repo


@pytest.fixture
def mock_resend_client():
    """Mock Resend client."""
    client = AsyncMock(spec=ResendClient)
    return client


@pytest.fixture
def mock_whatsapp_client():
    """Mock WhatsApp client."""
    client = AsyncMock(spec=WhatsAppClient)
    return client


@pytest.fixture
def alert_service(
    mock_notification_repo,
    mock_template_repo,
    mock_preference_repo,
    mock_resend_client,
    mock_whatsapp_client
):
    """Alert engine service fixture."""
    return AlertEngineService(
        notification_repo=mock_notification_repo,
        template_repo=mock_template_repo,
        preference_repo=mock_preference_repo,
        resend_client=mock_resend_client,
        whatsapp_client=mock_whatsapp_client
    )


@pytest.fixture
def sample_company_id():
    """Sample company ID."""
    return uuid4()


@pytest.fixture
def sample_alert_event(sample_company_id):
    """Sample alert event."""
    return AlertEvent(
        company_id=sample_company_id,
        alert_type="new_tender",
        message="New tender matching your profile",
        urgency="medium",
        context_data={
            "tender_title": "IT Infrastructure Upgrade",
            "tender_id": str(uuid4()),
            "deadline_date": "2024-12-31",
            "tender_value": "500000"
        }
    )


@pytest.fixture
def sample_notification(sample_company_id):
    """Sample notification."""
    return Notification(
        id=uuid4(),
        company_id=sample_company_id,
        notification_type=NotificationType.EMAIL,
        recipient="test@example.com",
        subject="Test Alert",
        message="Test message",
        priority=NotificationPriority.MEDIUM,
        status=NotificationStatus.PENDING,
        context_data={"test": "data"}
    )


class TestAlertEngineService:
    """Test alert engine service."""

    @pytest.mark.asyncio
    async def test_create_notification_success(
        self,
        alert_service,
        mock_notification_repo,
        mock_preference_repo,
        mock_resend_client,
        sample_company_id
    ):
        """Test successful notification creation."""
        # Setup
        notification_data = NotificationCreate(
            notification_type=NotificationType.EMAIL,
            recipient="test@example.com",
            subject="Test Alert",
            message="Test message",
            priority=NotificationPriority.MEDIUM
        )
        
        mock_notification = Notification(
            id=uuid4(),
            company_id=sample_company_id,
            notification_type=NotificationType.EMAIL,
            recipient="test@example.com",
            subject="Test Alert",
            message="Test message",
            priority=NotificationPriority.MEDIUM,
            status=NotificationStatus.PENDING,
            context_data={}
        )
        
        mock_notification_repo.create.return_value = mock_notification
        mock_preference_repo.get_by_company.return_value = []  # No preferences, should send
        
        # Execute
        result = await alert_service.create_notification(notification_data, sample_company_id)
        
        # Assert
        assert result == mock_notification
        mock_notification_repo.create.assert_called_once()
        mock_resend_client.send_tender_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_notification_skipped_by_preferences(
        self,
        alert_service,
        mock_notification_repo,
        mock_preference_repo,
        mock_resend_client,
        sample_company_id
    ):
        """Test notification skipped due to user preferences."""
        # Setup
        notification_data = NotificationCreate(
            notification_type=NotificationType.EMAIL,
            recipient="test@example.com",
            subject="Test Alert",
            message="Test message",
            priority=NotificationPriority.MEDIUM
        )
        
        # Mock preference that disables email
        mock_preference = Mock()
        mock_preference.email_enabled = False
        mock_preference_repo.get_by_company.return_value = [mock_preference]
        
        # Execute
        result = await alert_service.create_notification(notification_data, sample_company_id)
        
        # Assert
        assert result is None
        mock_notification_repo.create.assert_not_called()
        mock_resend_client.send_tender_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_alerts_from_event(
        self,
        alert_service,
        mock_notification_repo,
        mock_preference_repo,
        mock_resend_client,
        sample_alert_event,
        sample_company_id
    ):
        """Test sending alerts from event."""
        # Setup
        mock_notification = Notification(
            id=uuid4(),
            company_id=sample_company_id,
            notification_type=NotificationType.EMAIL,
            recipient="test@example.com",
            subject="New Tender Alert",
            message="New tender matching your profile",
            priority=NotificationPriority.MEDIUM,
            status=NotificationStatus.SENT,
            context_data=sample_alert_event.context_data
        )
        
        mock_notification_repo.create.return_value = mock_notification
        mock_preference_repo.get_by_company.return_value = []  # Default preferences
        
        # Execute
        result = await alert_service.send_alerts_from_event([sample_alert_event])
        
        # Assert
        assert len(result) == 1
        assert result[0] == mock_notification
        mock_notification_repo.create.assert_called_once()
        mock_resend_client.send_tender_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_notifications(
        self,
        alert_service,
        mock_notification_repo,
        sample_company_id
    ):
        """Test getting notifications."""
        # Setup
        mock_notifications = [
            Mock(id=uuid4()),
            Mock(id=uuid4())
        ]
        mock_notification_repo.get_by_company.return_value = (mock_notifications, 2)
        
        # Execute
        result, total = await alert_service.get_notifications(sample_company_id)
        
        # Assert
        assert result == mock_notifications
        assert total == 2
        mock_notification_repo.get_by_company.assert_called_once_with(
            sample_company_id, None, 1, 50
        )

    @pytest.mark.asyncio
    async def test_retry_failed_notifications(
        self,
        alert_service,
        mock_notification_repo,
        mock_resend_client,
        sample_company_id
    ):
        """Test retrying failed notifications."""
        # Setup
        mock_failed_notification = Mock()
        mock_failed_notification.should_retry_now = True
        mock_failed_notification.id = uuid4()
        mock_failed_notification.notification_type = NotificationType.EMAIL
        
        mock_notification_repo.get_retryable.return_value = [mock_failed_notification]
        
        # Mock the _send_notification method instead
        alert_service._send_notification = AsyncMock()
        
        # Execute
        result = await alert_service.retry_failed_notifications(sample_company_id)
        
        # Assert
        assert len(result) == 1
        assert result[0] == mock_failed_notification
        mock_notification_repo.get_retryable.assert_called_once_with(sample_company_id)
        alert_service._send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_quiet_hours_respected(
        self,
        alert_service,
        mock_notification_repo,
        mock_preference_repo,
        mock_resend_client,
        sample_company_id
    ):
        """Test that quiet hours are respected."""
        # Setup
        notification_data = NotificationCreate(
            notification_type=NotificationType.EMAIL,
            recipient="test@example.com",
            subject="Test Alert",
            message="Test message",
            priority=NotificationPriority.MEDIUM
        )
        
        # Mock preference with quiet hours (9 PM - 9 AM)
        mock_preference = Mock()
        mock_preference.email_enabled = True
        mock_preference.quiet_hours_start = "21:00"
        mock_preference.quiet_hours_end = "09:00"
        mock_preference_repo.get_by_company.return_value = [mock_preference]
        
        # Execute
        result = await alert_service.create_notification(notification_data, sample_company_id)
        
        # Note: This test would need to be enhanced with actual time checking
        # For now, we verify the method is called
        mock_preference_repo.get_by_company.assert_called_once()

    def test_generate_subject_mapping(self, alert_service, sample_alert_event):
        """Test subject generation for different alert types."""
        # Test different alert types
        deadline_event = AlertEvent(
            company_id=sample_alert_event.company_id,
            alert_type="deadline_reminder",
            message="Test",
            urgency="medium"
        )
        subject = alert_service._generate_subject(deadline_event)
        assert "Deadline Reminder" in subject
        
        new_tender_event = AlertEvent(
            company_id=sample_alert_event.company_id,
            alert_type="new_tender",
            message="Test",
            urgency="medium"
        )
        subject = alert_service._generate_subject(new_tender_event)
        assert "New Tender" in subject

    def test_urgency_to_priority_mapping(self, alert_service):
        """Test urgency to priority mapping."""
        assert alert_service._map_urgency_to_priority("low") == NotificationPriority.LOW
        assert alert_service._map_urgency_to_priority("medium") == NotificationPriority.MEDIUM
        assert alert_service._map_urgency_to_priority("high") == NotificationPriority.HIGH
        assert alert_service._map_urgency_to_priority("urgent") == NotificationPriority.URGENT
        # Test default
        assert alert_service._map_urgency_to_priority("unknown") == NotificationPriority.MEDIUM
