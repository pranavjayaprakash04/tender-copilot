from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from app.shared.tasks import BaseTask
from app.shared.logger import get_logger

from app.config import settings

from .repository import WhatsAppGatewayRepository

logger = get_logger()


class WhatsAppMessageTask(BaseTask):
    """Base task for WhatsApp message operations."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(
            "whatsapp_task_failed",
            task_id=task_id,
            error=str(exc),
            args=args,
            kwargs=kwargs,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        logger.warning(
            "whatsapp_task_retry",
            task_id=task_id,
            error=str(exc),
            args=args,
            kwargs=kwargs,
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(
            "whatsapp_task_success",
            task_id=task_id,
            result=retval,
            args=args,
            kwargs=kwargs,
        )
        super().on_success(retval, task_id, args, kwargs)


async def send_whatsapp_alert_task(
    company_id: UUID,
    tender_id: UUID | None = None,
    message_type: str = "alert",
    content: str | None = None,
    recipient_phone: str | None = None,
    template_name: str | None = None,
    template_variables: dict[str, Any] | None = None,
    media_url: str | None = None,
    priority: str = "normal",
) -> dict[str, Any]:
    """
    Send WhatsApp alert to company.
    
    Args:
        company_id: Target company ID
        tender_id: Related tender ID (optional)
        message_type: Type of message (alert, update, reminder, etc.)
        content: Message content (required if not using template)
        recipient_phone: Recipient phone number (optional, will use company default)
        template_name: WhatsApp template name (optional)
        template_variables: Variables for template (optional)
        media_url: Optional media URL
        priority: Message priority (low, normal, high)
    
    Returns:
        Dict with message status and details
    """
    task_id = str(uuid4())

    try:
        logger.info(
            "send_whatsapp_alert_task_started",
            task_id=task_id,
            company_id=company_id,
            tender_id=tender_id,
            message_type=message_type,
            priority=priority,
        )

        repository = WhatsAppGatewayRepository()

        # Check opt-in status
        opt_status = await repository.get_opt_status(company_id)
        if not opt_status or not opt_status.is_opted_in:
            logger.info(
                "whatsapp_not_sent_opted_out",
                task_id=task_id,
                company_id=company_id,
                is_opted_in=opt_status.is_opted_in if opt_status else False,
            )
            return {
                "status": "skipped",
                "reason": "opted_out",
                "message_id": None,
                "task_id": task_id,
            }

        # Get recipient phone number
        phone_to_use = recipient_phone or opt_status.phone_number
        if not phone_to_use:
            logger.error(
                "whatsapp_not_sent_no_phone",
                task_id=task_id,
                company_id=company_id,
            )
            return {
                "status": "failed",
                "reason": "no_phone_number",
                "message_id": None,
                "task_id": task_id,
            }

        # Generate message content if not provided
        if not content and not template_name:
            content = _generate_default_alert_content(message_type)

        # Create message log entry
        message_id = str(uuid4())
        await repository.create_message_log(
            company_id=company_id,
            message_id=message_id,
            direction="outbound",
            from_phone=settings.WHATSAPP_PHONE_NUMBER_ID,
            to_phone=phone_to_use,
            content=content or f"Template: {template_name}",
            message_type=message_type,
            status="pending",
            metadata={
                "tender_id": str(tender_id) if tender_id else None,
                "template_name": template_name,
                "template_variables": template_variables,
                "media_url": media_url,
                "priority": priority,
                "task_id": task_id,
            },
        )

        # Send message via WhatsApp API
        result = await _send_whatsapp_message(
            recipient_phone=phone_to_use,
            content=content,
            template_name=template_name,
            template_variables=template_variables,
            media_url=media_url,
        )

        # Update message log with result
        if result["status"] == "success":
            await repository.update_message_status(
                message_id=message_id,
                status="sent",
                sent_at=datetime.utcnow(),
            )

            # Increment message count
            await repository.increment_message_count(
                company_id=company_id,
                last_message_date=datetime.utcnow(),
            )

            logger.info(
                "whatsapp_alert_sent_successfully",
                task_id=task_id,
                company_id=company_id,
                message_id=message_id,
                whatsapp_message_id=result.get("whatsapp_message_id"),
            )

            return {
                "status": "success",
                "message_id": message_id,
                "whatsapp_message_id": result.get("whatsapp_message_id"),
                "task_id": task_id,
            }
        else:
            await repository.update_message_status(
                message_id=message_id,
                status="failed",
                error_message=result.get("error", "Unknown error"),
            )

            logger.error(
                "whatsapp_alert_send_failed",
                task_id=task_id,
                company_id=company_id,
                message_id=message_id,
                error=result.get("error"),
            )

            return {
                "status": "failed",
                "reason": result.get("error", "Unknown error"),
                "message_id": message_id,
                "task_id": task_id,
            }

    except Exception as e:
        logger.error(
            "send_whatsapp_alert_task_error",
            task_id=task_id,
            company_id=company_id,
            error=str(e),
        )

        return {
            "status": "error",
            "reason": str(e),
            "message_id": None,
            "task_id": task_id,
        }


async def _send_whatsapp_message(
    recipient_phone: str,
    content: str | None = None,
    template_name: str | None = None,
    template_variables: dict[str, Any] | None = None,
    media_url: str | None = None,
) -> dict[str, Any]:
    """
    Send message via WhatsApp Cloud API.
    
    Args:
        recipient_phone: Recipient phone number in E.164 format
        content: Message content for text messages
        template_name: Template name for template messages
        template_variables: Variables for template
        media_url: Optional media URL
    
    Returns:
        Dict with send result
    """
    try:
        # Prepare API request
        api_url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        # Build message payload
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
        }

        if template_name and template_variables:
            # Send template message
            payload["type"] = "template"
            payload["template"] = {
                "name": template_name,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(value)}
                            for value in template_variables.values()
                        ],
                    }
                ],
            }
        elif content:
            # Send text message
            payload["type"] = "text"
            payload["text"] = {"body": content}

            if media_url:
                # Add media if provided
                payload["type"] = "image" if media_url.endswith(('.jpg', '.jpeg', '.png')) else "document"
                payload[payload["type"]] = {
                    "link": media_url,
                    "caption": content,
                }
        else:
            return {
                "status": "failed",
                "error": "No content or template provided",
            }

        # Send request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")

                logger.info(
                    "whatsapp_api_send_success",
                    recipient=recipient_phone,
                    message_id=message_id,
                    template_name=template_name,
                )

                return {
                    "status": "success",
                    "whatsapp_message_id": message_id,
                }
            else:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown API error")

                logger.error(
                    "whatsapp_api_send_failed",
                    recipient=recipient_phone,
                    status_code=response.status_code,
                    error_message=error_message,
                    error_data=error_data,
                )

                return {
                    "status": "failed",
                    "error": error_message,
                    "error_code": response.status_code,
                }

    except httpx.TimeoutException:
        logger.error(
            "whatsapp_api_timeout",
            recipient=recipient_phone,
        )
        return {
            "status": "failed",
            "error": "API timeout",
        }
    except Exception as e:
        logger.error(
            "whatsapp_api_error",
            recipient=recipient_phone,
            error=str(e),
        )
        return {
            "status": "failed",
            "error": str(e),
        }


def _generate_default_alert_content(message_type: str) -> str:
    """Generate default alert content based on message type."""

    if message_type == "new_tender":
        return (
            "🔥 *New Tender Alert!*\n\n"
            "A new tender matching your profile has been posted.\n"
            "Check your dashboard for details and bid submission.\n\n"
            "Reply STATUS to see all active opportunities."
        )
    elif message_type == "deadline_reminder":
        return (
            "⏰ *Deadline Reminder!*\n\n"
            "You have tender submissions due soon.\n"
            "Don't miss out on these opportunities.\n\n"
            "Reply LIST to see urgent tenders."
        )
    elif message_type == "bid_update":
        return (
            "📝 *Bid Status Update*\n\n"
            "There's an update on your bid submission.\n"
            "Check your dashboard for the latest status.\n\n"
            "Reply STATUS for current bid information."
        )
    elif message_type == "payment_reminder":
        return (
            "💰 *Payment Reminder*\n\n"
            "You have upcoming EMD or other payments due.\n"
            "Ensure timely payment to avoid bid disqualification.\n\n"
            "Check your dashboard for payment details."
        )
    else:
        return (
            "📢 *Tender Notification*\n\n"
            "You have a new update from Tender Copilot.\n"
            "Check your dashboard for more information.\n\n"
            "Reply HELP for available commands."
        )


# Celery task definitions
send_whatsapp_alert = WhatsAppMessageTask().task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="whatsapp_gateway.send_whatsapp_alert",
)(send_whatsapp_alert_task)


async def send_bulk_whatsapp_alerts_task(
    company_ids: list[UUID],
    message_type: str = "alert",
    content: str | None = None,
    template_name: str | None = None,
    template_variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Send bulk WhatsApp alerts to multiple companies.
    
    Args:
        company_ids: List of company IDs to send alerts to
        message_type: Type of message
        content: Message content (required if not using template)
        template_name: WhatsApp template name (optional)
        template_variables: Variables for template (optional)
    
    Returns:
        Dict with bulk send results
    """
    task_id = str(uuid4())

    try:
        logger.info(
            "send_bulk_whatsapp_alerts_started",
            task_id=task_id,
            company_count=len(company_ids),
            message_type=message_type,
        )

        results = {
            "total_companies": len(company_ids),
            "successful_sends": 0,
            "failed_sends": 0,
            "skipped_sends": 0,
            "results": [],
        }

        for company_id in company_ids:
            try:
                result = await send_whatsapp_alert_task(
                    company_id=company_id,
                    message_type=message_type,
                    content=content,
                    template_name=template_name,
                    template_variables=template_variables,
                )

                results["results"].append({
                    "company_id": company_id,
                    "status": result["status"],
                    "message_id": result.get("message_id"),
                })

                if result["status"] == "success":
                    results["successful_sends"] += 1
                elif result["status"] == "skipped":
                    results["skipped_sends"] += 1
                else:
                    results["failed_sends"] += 1

            except Exception as e:
                logger.error(
                    "bulk_whatsapp_send_company_failed",
                    task_id=task_id,
                    company_id=company_id,
                    error=str(e),
                )
                results["failed_sends"] += 1
                results["results"].append({
                    "company_id": company_id,
                    "status": "error",
                    "error": str(e),
                })

        logger.info(
            "send_bulk_whatsapp_alerts_completed",
            task_id=task_id,
            successful=results["successful_sends"],
            failed=results["failed_sends"],
            skipped=results["skipped_sends"],
        )

        return {
            "task_id": task_id,
            "status": "completed",
            **results,
        }

    except Exception as e:
        logger.error(
            "send_bulk_whatsapp_alerts_error",
            task_id=task_id,
            error=str(e),
        )

        return {
            "task_id": task_id,
            "status": "error",
            "error": str(e),
        }


# Celery task for bulk sends
send_bulk_whatsapp_alerts = WhatsAppMessageTask().task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    name="whatsapp_gateway.send_bulk_whatsapp_alerts",
)(send_bulk_whatsapp_alerts_task)
