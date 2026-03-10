from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


class WhatsAppClient:
    """WhatsApp client using Meta API with httpx for async operations."""

    def __init__(self) -> None:
        self.base_url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}"
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN

    async def send_message(
        self,
        to: str,
        message: str,
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """Send WhatsApp message using Meta API."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {
                        "body": message
                    }
                }

                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }

                response = await client.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )

                response.raise_for_status()

                result = response.json()

                logger.info(
                    "whatsapp_message_sent",
                    trace_id=trace_id,
                    to=to,
                    message_id=result.get("messages", [{}])[0].get("id")
                )

                return result

            except httpx.HTTPError as e:
                logger.error(
                    "whatsapp_http_error",
                    trace_id=trace_id,
                    to=to,
                    status_code=e.response.status_code if e.response else None,
                    error=str(e)
                )
                raise
            except Exception as e:
                logger.error(
                    "whatsapp_send_error",
                    trace_id=trace_id,
                    to=to,
                    error=str(e)
                )
                raise

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        components: list[dict[str, Any]],
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """Send WhatsApp template message."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": "ta"},  # Default to Tamil
                        "components": components
                    }
                }

                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }

                response = await client.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )

                response.raise_for_status()

                result = response.json()

                logger.info(
                    "whatsapp_template_sent",
                    trace_id=trace_id,
                    to=to,
                    template_name=template_name,
                    message_id=result.get("messages", [{}])[0].get("id")
                )

                return result

            except httpx.HTTPError as e:
                logger.error(
                    "whatsapp_template_http_error",
                    trace_id=trace_id,
                    to=to,
                    template_name=template_name,
                    status_code=e.response.status_code if e.response else None,
                    error=str(e)
                )
                raise
            except Exception as e:
                logger.error(
                    "whatsapp_template_send_error",
                    trace_id=trace_id,
                    to=to,
                    template_name=template_name,
                    error=str(e)
                )
                raise

    async def verify_webhook(
        self,
        hub_mode: str,
        hub_challenge: str,
        hub_verify_token: str
    ) -> str:
        """Verify WhatsApp webhook."""
        if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_APP_SECRET:
            return hub_challenge
        else:
            raise ValueError("Webhook verification failed")

    async def mark_message_as_read(
        self,
        message_id: str,
        trace_id: str | None = None
    ) -> dict[str, Any]:
        """Mark WhatsApp message as read."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id
                }

                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }

                response = await client.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )

                response.raise_for_status()

                result = response.json()

                logger.info(
                    "whatsapp_message_marked_read",
                    trace_id=trace_id,
                    message_id=message_id,
                    success=result.get("success", False)
                )

                return result

            except httpx.HTTPError as e:
                logger.error(
                    "whatsapp_mark_read_http_error",
                    trace_id=trace_id,
                    message_id=message_id,
                    status_code=e.response.status_code if e.response else None,
                    error=str(e)
                )
                raise
            except Exception as e:
                logger.error(
                    "whatsapp_mark_read_error",
                    trace_id=trace_id,
                    message_id=message_id,
                    error=str(e)
                )
                raise
