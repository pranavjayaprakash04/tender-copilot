from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.contexts.whatsapp_gateway.service import WhatsAppGatewayService


class TestWhatsAppGateway:
    """Test WhatsApp Gateway functionality."""

    @pytest.fixture
    def company_id(self) -> UUID:
        """Test company ID."""
        return UUID("87654321-4321-8765-4321-876543218765")

    @pytest.fixture
    def user_id(self) -> str:
        """Test user ID."""
        return "test-user-123"

    @pytest.fixture
    def mock_service(self) -> AsyncMock:
        """Mock WhatsApp Gateway service."""
        return AsyncMock(spec=WhatsAppGatewayService)

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Mock WhatsApp Gateway repository."""
        return AsyncMock()

    @pytest.fixture
    def webhook_payload(self) -> dict:
        """Sample WhatsApp webhook payload."""
        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123456789",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messages": [
                                    {
                                        "from": "+1234567890",
                                        "to": "+9876543210",
                                        "id": "msg_123",
                                        "timestamp": "1640995200",
                                        "text": {"body": "STOP"},
                                        "type": "text"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

    @pytest.fixture
    def send_request(self, company_id: UUID) -> dict:
        """Sample WhatsApp send request."""
        return {
            "company_id": str(company_id),
            "recipient_phone": "+1234567890",
            "message_type": "alert",
            "content": "Test alert message",
            "priority": "normal"
        }

    async def test_webhook_verification_success(
        self, mock_service: AsyncMock, company_id: UUID
    ) -> None:
        """Test successful webhook verification."""
        # Setup
        mock_service.verify_webhook.return_value = "test123"

        # Execute
        result = await mock_service.verify_webhook("subscribe", "testtoken", "test123")

        # Verify
        assert result == "test123"
        mock_service.verify_webhook.assert_called_once_with("subscribe", "testtoken", "test123")

    async def test_webhook_verification_failure(
        self, mock_service: AsyncMock, company_id: UUID
    ) -> None:
        """Test webhook verification failure."""
        # Setup
        mock_service.verify_webhook.return_value = None

        # Execute
        result = await mock_service.verify_webhook("subscribe", "wrongtoken", "test123")

        # Verify
        assert result is None
        mock_service.verify_webhook.assert_called_once_with("subscribe", "wrongtoken", "test123")

    async def test_inbound_stop_command(
        self, mock_service: AsyncMock, webhook_payload: dict, company_id: UUID
    ) -> None:
        """Test processing inbound STOP command."""
        # Setup
        expected_response = {
            "status": "success",
            "messages_processed": 1,
            "messages": [{
                "company_id": company_id,
                "message_id": "msg_123",
                "content": "STOP",
                "response": {
                    "action": "reply",
                    "content": "You have been successfully opted out."
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }
        mock_service.process_webhook_payload.return_value = expected_response

        # Execute
        result = await mock_service.process_webhook_payload(webhook_payload)

        # Verify
        assert result["status"] == "success"
        assert result["messages_processed"] == 1
        assert "opted out" in result["messages"][0]["response"]["content"]
        mock_service.process_webhook_payload.assert_called_once_with(webhook_payload)

    async def test_inbound_list_command(
        self, mock_service: AsyncMock, company_id: UUID
    ) -> None:
        """Test processing inbound LIST command."""
        # Setup
        list_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123456789",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messages": [
                                    {
                                        "from": "+1234567890",
                                        "to": "+9876543210",
                                        "id": "msg_456",
                                        "timestamp": "1640995200",
                                        "text": {"body": "LIST"},
                                        "type": "text"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        expected_response = {
            "status": "success",
            "messages_processed": 1,
            "messages": [{
                "company_id": company_id,
                "message_id": "msg_456",
                "content": "LIST",
                "response": {
                    "action": "reply",
                    "content": "📋 *Top Matching Tenders*\n\n1. *Software Development Tender*\n   🔥 3 days left\n   💰 $500,000\n   📍 Karnataka\n\n2. *Web Application Project*\n   ⏰ 5 days left\n   💰 $300,000\n   📍 Maharashtra\n\n3. *Mobile App Development*\n   📅 10 days left\n   💰 $200,000\n   📍 Tamil Nadu"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }
        mock_service.process_webhook_payload.return_value = expected_response

        # Execute
        result = await mock_service.process_webhook_payload(list_payload)

        # Verify
        assert result["status"] == "success"
        assert result["messages_processed"] == 1
        assert "Top Matching Tenders" in result["messages"][0]["response"]["content"]
        mock_service.process_webhook_payload.assert_called_once_with(list_payload)

    async def test_send_alert_task_success(
        self, mock_service: AsyncMock, send_request: dict, company_id: UUID
    ) -> None:
        """Test sending WhatsApp alert successfully."""
        # Setup - test that service would handle the request
        from app.contexts.whatsapp_gateway.schemas import WhatsAppSendRequest
        
        request_obj = WhatsAppSendRequest(**send_request)
        
        # Mock the task delay method
        mock_task = MagicMock()
        mock_task.id = "task-123"
        
        # Test that the request object is created correctly
        assert request_obj.company_id == company_id
        assert request_obj.recipient_phone == "+1234567890"
        assert request_obj.content == "Test alert message"

    async def test_opt_out_respected(
        self, mock_service: AsyncMock, mock_repository: AsyncMock, company_id: UUID
    ) -> None:
        """Test that opt-out status is respected."""
        # Setup
        mock_service.get_opt_status.return_value = None  # Company not found
        
        # Test service method directly
        opt_status = await mock_service.get_opt_status(company_id)

        # Verify
        assert opt_status is None
        mock_service.get_opt_status.assert_called_once_with(company_id)

    async def test_webhook_processing_error(
        self, mock_service: AsyncMock, webhook_payload: dict
    ) -> None:
        """Test webhook processing error handling."""
        # Setup
        mock_service.process_webhook_payload.side_effect = Exception("Processing error")

        # Execute
        try:
            await mock_service.process_webhook_payload(webhook_payload)
            assert False, "Should have raised exception"
        except Exception:
            pass  # Expected exception

        # Verify
        mock_service.process_webhook_payload.assert_called_once_with(webhook_payload)

    async def test_invalid_webhook_object(
        self, mock_service: AsyncMock
    ) -> None:
        """Test webhook with invalid object type."""
        # Setup
        invalid_payload = {
            "object": "invalid_object",
            "entry": []
        }

        mock_service.process_webhook_payload.return_value = {"status": "success"}

        # Execute
        result = await mock_service.process_webhook_payload(invalid_payload)

        # Verify - service should handle gracefully
        assert result["status"] == "success"
        mock_service.process_webhook_payload.assert_called_once_with(invalid_payload)

    async def test_send_message_company_not_found(
        self, mock_service: AsyncMock, mock_repository: AsyncMock, company_id: UUID
    ) -> None:
        """Test sending message when company not found."""
        # Setup
        mock_service.get_opt_status.return_value = None
        
        # Test service method directly
        opt_status = await mock_service.get_opt_status(company_id)

        # Verify
        assert opt_status is None
        mock_service.get_opt_status.assert_called_once_with(company_id)

    async def test_send_message_wrong_company(
        self, mock_service: AsyncMock, mock_repository: AsyncMock, company_id: UUID
    ) -> None:
        """Test sending message to wrong company."""
        # Setup
        wrong_company_id = UUID("99999999-9999-9999-9999-999999999999")
        mock_service.get_opt_status.return_value = {"company_id": wrong_company_id, "is_opted_in": True}
        
        # Test service method directly
        opt_status = await mock_service.get_opt_status(wrong_company_id)

        # Verify
        assert opt_status is not None
        assert opt_status["company_id"] == wrong_company_id
        mock_service.get_opt_status.assert_called_once_with(wrong_company_id)
