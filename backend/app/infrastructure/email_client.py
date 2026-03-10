"""Email client for sending notifications."""

from __future__ import annotations

from typing import Any, Dict, Optional
import structlog


logger = structlog.get_logger()


class EmailClient:
    """Simple email client for MVP."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        from_email: str = "noreply@example.com"
    ) -> Dict[str, Any]:
        """Send an email (placeholder implementation)."""
        logger.info(
            "email_sent",
            to=to,
            subject=subject,
            from_email=from_email,
            content_length=len(html_content)
        )
        
        return {
            "success": True,
            "message_id": "mock_message_id",
            "status": "sent"
        }
    
    async def send_template_email(
        self,
        to: str,
        template_id: str,
        template_data: Dict[str, Any],
        from_email: str = "noreply@example.com"
    ) -> Dict[str, Any]:
        """Send a template email (placeholder implementation)."""
        logger.info(
            "template_email_sent",
            to=to,
            template_id=template_id,
            template_data=template_data,
            from_email=from_email
        )
        
        return {
            "success": True,
            "message_id": "mock_message_id",
            "status": "sent"
        }
