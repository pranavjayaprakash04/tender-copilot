from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.shared.logger import get_logger

from app.config import settings
from app.contexts.company_profile.service import CompanyProfileService
from app.contexts.tender_discovery.service import TenderDiscoveryService
from app.shared.events import DomainEventPublisher

from .repository import WhatsAppGatewayRepository
from .schemas import (
    WhatsAppStatsResponse,
    WhatsAppStatusResponse,
    WhatsAppWebhookPayload,
)

logger = get_logger()


class WhatsAppGatewayService:
    """Service for WhatsApp gateway operations."""

    def __init__(
        self,
        repository: WhatsAppGatewayRepository | None = None,
        company_service: CompanyProfileService | None = None,
        tender_service: TenderDiscoveryService | None = None,
    ) -> None:
        self.repository = repository or WhatsAppGatewayRepository()
        self.company_service = company_service or CompanyProfileService()
        self.tender_service = tender_service or TenderDiscoveryService()
        self.event_publisher = DomainEventPublisher()

    async def process_webhook_payload(self, payload: WhatsAppWebhookPayload) -> dict[str, Any]:
        """Process incoming WhatsApp webhook payload."""
        try:
            messages = []

            for entry in payload.entry:
                for change in entry.changes:
                    if change.get("field") == "messages":
                        messages.extend(change.get("value", {}).get("messages", []))

            processed_messages = []
            for message_data in messages:
                processed_message = await self._process_inbound_message(message_data)
                if processed_message:
                    processed_messages.append(processed_message)

            return {
                "status": "success",
                "messages_processed": len(processed_messages),
                "messages": processed_messages,
            }

        except Exception as e:
            logger.error(
                "webhook_processing_failed",
                error=str(e),
                payload=payload.model_dump() if hasattr(payload, 'model_dump') else str(payload),
            )
            return {
                "status": "error",
                "error": str(e),
                "messages_processed": 0,
            }

    async def _process_inbound_message(self, message_data: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single inbound message."""
        try:
            # Extract message details
            from_phone = message_data.get("from", "")
            to_phone = message_data.get("to", "")
            message_id = message_data.get("id", "")
            timestamp = datetime.fromtimestamp(int(message_data.get("timestamp", 0)))

            # Get message content based on type
            message_type = message_data.get("type", "text")
            content = ""

            if message_type == "text":
                content = message_data.get("text", {}).get("body", "")
            elif message_type == "interactive":
                # Handle interactive messages (buttons, etc.)
                interactive_data = message_data.get("interactive", {})
                if interactive_data.get("type") == "button_reply":
                    content = interactive_data.get("button_reply", {}).get("title", "")
                elif interactive_data.get("type") == "list_reply":
                    content = interactive_data.get("list_reply", {}).get("title", "")
            else:
                content = f"[{message_type.upper()} message]"

            # Find company by phone number
            company = await self._find_company_by_phone(from_phone)
            if not company:
                logger.warning(
                    "company_not_found_for_phone",
                    phone=from_phone,
                    message_id=message_id,
                )
                return None

            # Get or create opt status
            opt_status = await self.repository.get_or_create_opt_status(
                company_id=company.id,
                phone_number=from_phone,
            )

            # Check if opted out
            if not opt_status.is_opted_in:
                logger.info(
                    "message_from_opted_out_user",
                    company_id=company.id,
                    phone=from_phone,
                    message_id=message_id,
                )
                return None

            # Log the inbound message
            await self.repository.create_message_log(
                company_id=company.id,
                message_id=message_id,
                direction="inbound",
                from_phone=from_phone,
                to_phone=to_phone,
                content=content,
                message_type=message_type,
                status="received",
            )

            # Increment message count
            await self.repository.increment_message_count(
                company_id=company.id,
                last_message_date=timestamp,
            )

            # Process command
            response = await self._process_command(company.id, content, from_phone, to_phone)

            return {
                "company_id": company.id,
                "message_id": message_id,
                "content": content,
                "response": response,
                "timestamp": timestamp.isoformat(),
            }

        except Exception as e:
            logger.error(
                "inbound_message_processing_failed",
                error=str(e),
                message_data=message_data,
            )
            return None

    async def _find_company_by_phone(self, phone: str) -> Any | None:
        """Find company by phone number."""
        try:
            # This would typically query the company profile by phone
            # For now, we'll use a placeholder implementation
            companies = await self.company_service.get_companies()
            for company in companies:
                # Check if phone matches any company contact info
                # This is a simplified approach - in production, you'd have a proper phone field
                if hasattr(company, 'phone') and company.phone == phone:
                    return company
            return None
        except Exception as e:
            logger.error(
                "find_company_by_phone_failed",
                error=str(e),
                phone=phone,
            )
            return None

    async def _process_command(
        self, company_id: UUID, content: str, from_phone: str, to_phone: str
    ) -> dict[str, Any]:
        """Process inbound command and generate response."""
        try:
            content_upper = content.strip().upper()

            if content_upper == "STOP":
                return await self._handle_stop_command(company_id)
            elif content_upper == "START":
                return await self._handle_start_command(company_id)
            elif content_upper == "STATUS":
                return await self._handle_status_command(company_id)
            elif content_upper == "LIST":
                return await self._handle_list_command(company_id)
            elif content_upper == "HELP":
                return await self._handle_help_command()
            else:
                return await self._handle_unknown_command(content)

        except Exception as e:
            logger.error(
                "command_processing_failed",
                error=str(e),
                company_id=company_id,
                content=content,
            )
            return {
                "action": "reply",
                "content": "Sorry, I encountered an error processing your request. Please try again.",
            }

    async def _handle_stop_command(self, company_id: UUID) -> dict[str, Any]:
        """Handle STOP command - opt out user."""
        try:
            await self.repository.update_opt_status(company_id, is_opted_in=False)

            logger.info(
                "user_opted_out",
                company_id=company_id,
            )

            return {
                "action": "reply",
                "content": "You have been successfully opted out. You will no longer receive WhatsApp notifications. Reply START to opt back in.",
            }
        except Exception as e:
            logger.error(
                "stop_command_failed",
                error=str(e),
                company_id=company_id,
            )
            return {
                "action": "reply",
                "content": "Sorry, I couldn't process your opt-out request. Please try again later.",
            }

    async def _handle_start_command(self, company_id: UUID) -> dict[str, Any]:
        """Handle START command - opt in user."""
        try:
            await self.repository.update_opt_status(company_id, is_opted_in=True)

            logger.info(
                "user_opted_in",
                company_id=company_id,
            )

            return {
                "action": "reply",
                "content": "Welcome back! You have been successfully opted in. You will receive WhatsApp notifications for new tenders and updates.",
            }
        except Exception as e:
            logger.error(
                "start_command_failed",
                error=str(e),
                company_id=company_id,
            )
            return {
                "action": "reply",
                "content": "Sorry, I couldn't process your opt-in request. Please try again later.",
            }

    async def _handle_status_command(self, company_id: UUID) -> dict[str, Any]:
        """Handle STATUS command - reply with active tender count."""
        try:
            # Get active tenders for the company
            filters = {"is_active": True}
            tenders = await self.tender_service.get_tenders(company_id, filters)
            active_count = len(tenders)

            # Get bid statistics
            bids = await self.tender_service.get_bids(company_id) if hasattr(self.tender_service, 'get_bids') else []
            active_bids = len([bid for bid in bids if bid.status in ["draft", "submitted", "under_evaluation"]])

            status_message = (
                f"📊 *Your Status*\n"
                f"🔥 Active Tenders: {active_count}\n"
                f"📝 Active Bids: {active_bids}\n\n"
                f"Reply LIST to see top matching tenders."
            )

            return {
                "action": "reply",
                "content": status_message,
            }
        except Exception as e:
            logger.error(
                "status_command_failed",
                error=str(e),
                company_id=company_id,
            )
            return {
                "action": "reply",
                "content": "Sorry, I couldn't retrieve your status. Please try again later.",
            }

    async def _handle_list_command(self, company_id: UUID) -> dict[str, Any]:
        """Handle LIST command - reply with top 3 matching tenders."""
        try:
            # Get top tenders for the company
            tenders = await self.tender_service.get_tenders(
                company_id,
                filters={"is_active": True, "limit": 3}
            )

            if not tenders:
                return {
                    "action": "reply",
                    "content": "No active tenders found matching your profile. Reply HELP for available commands.",
                }

            list_message = "📋 *Top Matching Tenders*\n\n"
            for i, tender in enumerate(tenders[:3], 1):
                deadline_days = (tender.bid_submission_deadline - datetime.utcnow()).days
                urgency = "🔥" if deadline_days <= 3 else "⏰" if deadline_days <= 7 else "📅"

                list_message += (
                    f"{i}. *{tender.title[:50]}{'...' if len(tender.title) > 50 else ''}*\n"
                    f"   {urgency} {deadline_days} days left\n"
                    f"   💰 {tender.estimated_value or 'Value not disclosed'}\n"
                    f"   📍 {tender.state or 'Location not specified'}\n\n"
                )

            list_message += "Reply STATUS for more details or HELP for other commands."

            return {
                "action": "reply",
                "content": list_message,
            }
        except Exception as e:
            logger.error(
                "list_command_failed",
                error=str(e),
                company_id=company_id,
            )
            return {
                "action": "reply",
                "content": "Sorry, I couldn't retrieve tender listings. Please try again later.",
            }

    async def _handle_help_command(self) -> dict[str, Any]:
        """Handle HELP command - show available commands."""
        help_message = (
            "🤖 *Tender Copilot WhatsApp Help*\n\n"
            "📋 *Available Commands:*\n"
            "• STATUS - Check your active tenders and bids\n"
            "• LIST - View top 3 matching tenders\n"
            "• STOP - Opt out of notifications\n"
            "• START - Opt back in to notifications\n"
            "• HELP - Show this help message\n\n"
            "💡 *Tips:*\n"
            "• You'll receive automatic alerts for new tenders\n"
            "• Reply STOP anytime to unsubscribe\n"
            "• Contact support for more help"
        )

        return {
            "action": "reply",
            "content": help_message,
        }

    async def _handle_unknown_command(self, content: str) -> dict[str, Any]:
        """Handle unknown commands."""
        response = (
            f"❓ I didn't understand: *{content[:30]}{'...' if len(content) > 30 else ''}*\n\n"
            "📋 *Available Commands:*\n"
            "• STATUS - Check your active tenders\n"
            "• LIST - View matching tenders\n"
            "• HELP - Show all commands\n\n"
            "Reply HELP for more information."
        )

        return {
            "action": "reply",
            "content": response,
        }

    async def get_opt_status(self, company_id: UUID) -> WhatsAppStatusResponse | None:
        """Get WhatsApp opt-in status for a company."""
        try:
            opt_status = await self.repository.get_opt_status(company_id)
            if not opt_status:
                return None

            # Get message statistics
            sent_messages = await self.repository.get_message_logs(
                company_id=company_id,
                direction="outbound",
                limit=1,
            )
            received_messages = await self.repository.get_message_logs(
                company_id=company_id,
                direction="inbound",
                limit=1,
            )

            last_sent_content = sent_messages[0].content if sent_messages else None

            return WhatsAppStatusResponse(
                company_id=opt_status.company_id,
                phone_number=opt_status.phone_number,
                is_opted_in=opt_status.is_opted_in,
                opt_in_date=opt_status.opt_in_date,
                opt_out_date=opt_status.opt_out_date,
                last_message_date=opt_status.last_message_date,
                total_messages_sent=len(sent_messages),
                total_messages_received=len(received_messages),
                last_message_content=last_sent_content,
            )

        except Exception as e:
            logger.error(
                "get_opt_status_failed",
                error=str(e),
                company_id=company_id,
            )
            return None

    async def get_whatsapp_stats(self) -> WhatsAppStatsResponse:
        """Get WhatsApp gateway statistics."""
        try:
            stats = await self.repository.get_whatsapp_stats()

            # Get recent activity
            recent_logs = await self.repository.get_message_logs(limit=10)

            return WhatsAppStatsResponse(
                total_companies=stats["total_companies"],
                opted_in_companies=stats["opted_in_companies"],
                opted_out_companies=stats["opted_out_companies"],
                total_messages_sent=stats["total_messages_sent"],
                total_messages_delivered=stats["total_messages_delivered"],
                total_messages_failed=stats["total_messages_failed"],
                delivery_rate=stats["delivery_rate"],
                messages_by_type=stats["messages_by_type"],
                recent_activity=recent_logs,
            )

        except Exception as e:
            logger.error(
                "get_whatsapp_stats_failed",
                error=str(e),
            )
            # Return empty stats on error
            return WhatsAppStatsResponse(
                total_companies=0,
                opted_in_companies=0,
                opted_out_companies=0,
                total_messages_sent=0,
                total_messages_delivered=0,
                total_messages_failed=0,
                delivery_rate=0.0,
                messages_by_type={},
                recent_activity=[],
            )

    async def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        """Verify WhatsApp webhook using WHATSAPP_VERIFY_TOKEN env var."""
        try:
            import hmac as hmac_lib
            # Use WHATSAPP_VERIFY_TOKEN for hub.verify_token comparison
            # WHATSAPP_APP_SECRET is reserved for HMAC-SHA256 payload signature verification
            expected_token = settings.WHATSAPP_VERIFY_TOKEN or ""
            if not expected_token:
                logger.warning(
                    "whatsapp_verify_token_not_configured",
                    detail="Set WHATSAPP_VERIFY_TOKEN env var"
                )
                return None
            if mode == "subscribe" and hmac_lib.compare_digest(expected_token, token):
                return challenge
            return None
        except Exception as e:
            logger.error(
                "webhook_verification_failed",
                error=str(e),
                mode=mode,
            )
            return None
