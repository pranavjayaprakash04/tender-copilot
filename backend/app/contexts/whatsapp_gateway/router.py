from __future__ import annotations

from typing import Any
from uuid import UUID

from app.dependencies import get_current_user_id, get_current_company_id, get_trace_id
from app.shared.schemas import BaseResponse
from app.shared.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import PlainTextResponse

from .schemas import (
    WhatsAppSendRequest,
    WhatsAppSendResponse,
    WhatsAppStatsResponse,
    WhatsAppStatusResponse,
    WhatsAppWebhookPayload,
)
from .service import WhatsAppGatewayService
from .tasks import send_bulk_whatsapp_alerts, send_whatsapp_alert

logger = get_logger()

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Gateway"])


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> PlainTextResponse:
    """
    Verify WhatsApp webhook endpoint.
    
    Meta/Facebook will call this endpoint when setting up the webhook
    to verify the endpoint is valid.
    """
    try:
        service = WhatsAppGatewayService()
        challenge = await service.verify_webhook(hub_mode, hub_verify_token, hub_challenge)

        if challenge:
            logger.info(
                "webhook_verification_success",
                mode=hub_mode,
                token=hub_verify_token[:10] + "...",  # Log partial token for security
            )
            return PlainTextResponse(content=challenge, status_code=200)
        else:
            logger.warning(
                "webhook_verification_failed",
                mode=hub_mode,
                token=hub_verify_token[:10] + "...",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Webhook verification failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "webhook_verification_error",
            error=str(e),
            mode=hub_mode,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during webhook verification"
        )


@router.post("/webhook")
async def receive_webhook(payload: WhatsAppWebhookPayload) -> BaseResponse[dict[str, Any]]:
    """
    Receive incoming WhatsApp webhook messages.
    
    This endpoint receives messages from WhatsApp users,
    processes commands, and handles responses.
    """
    try:
        service = WhatsAppGatewayService()

        # Process the webhook payload
        result = await service.process_webhook_payload(payload)

        logger.info(
            "webhook_processed",
            status=result["status"],
            messages_processed=result["messages_processed"],
        )

        return BaseResponse(
            data=result,
            message="Webhook processed successfully"
        )

    except Exception as e:
        logger.error(
            "webhook_processing_error",
            error=str(e),
            payload_type=type(payload).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook payload"
        )


@router.post("/send")
async def send_whatsapp_message(
    request: WhatsAppSendRequest,
    user_id: str = Depends(get_current_user_id),
) -> BaseResponse[WhatsAppSendResponse]:
    """
    Send WhatsApp message (internal endpoint).
    
    This endpoint allows internal services to send WhatsApp messages
    to opted-in users. Requires authentication.
    """
    try:
        # Get company from current user ID
        from app.contexts.company_profile.service import CompanyProfileService
        company_service = CompanyProfileService()
        companies = await company_service.get_companies()
        company = None
        for comp in companies:
            if hasattr(comp, 'user_id') and comp.user_id == user_id:
                company = comp
                break
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found for user"
            )

        # Validate company ID matches request
        if company.id != request.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot send messages to other companies"
            )

        # Queue the WhatsApp message task
        task_result = send_whatsapp_alert.delay(
            company_id=request.company_id,
            tender_id=None,  # Can be extended to include tender_id
            message_type=request.message_type,
            content=request.content,
            recipient_phone=request.recipient_phone,
            template_name=request.template_name,
            template_variables=request.template_variables,
            media_url=request.media_url,
            priority=request.priority,
        )

        logger.info(
            "whatsapp_message_queued",
            company_id=request.company_id,
            task_id=task_result.id,
            message_type=request.message_type,
        )

        # Return immediate response
        response = WhatsAppSendResponse(
            message_id=task_result.id,
            status="queued",
            error_message=None,
        )

        return BaseResponse(
            data=response,
            message="WhatsApp message queued successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "send_whatsapp_message_error",
            error=str(e),
            company_id=request.company_id if request else None,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue WhatsApp message"
        )


@router.post("/send-bulk")
async def send_bulk_whatsapp_messages(
    company_ids: list[UUID],
    message_type: str = "alert",
    content: str | None = None,
    template_name: str | None = None,
    template_variables: dict[str, Any] | None = None,
    user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[dict[str, Any]]:
    """
    Send bulk WhatsApp messages (internal endpoint).
    
    This endpoint allows internal services to send WhatsApp messages
    to multiple companies. Requires authentication.
    """
    try:
        # Validate user permissions for bulk operations
        from app.contexts.company_profile.service import CompanyProfileService
        company_service = CompanyProfileService()
        companies = await company_service.get_companies()
        company = None
        for comp in companies:
            if hasattr(comp, 'user_id') and comp.user_id == user_id:
                company = comp
                break
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found for user"
            )

        # For now, only allow admin users to send bulk messages
        if user_id != "admin":  # Simplified check for testing
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can send bulk messages"
            )

        # Queue the bulk WhatsApp message task
        task_result = send_bulk_whatsapp_alerts.delay(
            company_ids=company_ids,
            message_type=message_type,
            content=content,
            template_name=template_name,
            template_variables=template_variables,
        )

        logger.info(
            "bulk_whatsapp_messages_queued",
            company_count=len(company_ids),
            task_id=task_result.id,
            message_type=message_type,
            requested_by=current_user["id"],
        )

        return BaseResponse(
            data={
                "task_id": task_result.id,
                "company_count": len(company_ids),
                "message_type": message_type,
                "status": "queued",
            },
            message="Bulk WhatsApp messages queued successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "send_bulk_whatsapp_messages_error",
            error=str(e),
            company_count=len(company_ids) if company_ids else 0,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue bulk WhatsApp messages"
        )


@router.get("/status/{company_id}")
async def get_whatsapp_status(
    company_id: UUID,
    user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[WhatsAppStatusResponse]:
    """
    Get WhatsApp opt-in status for a company.
    
    Returns the current opt-in status, message statistics,
    and other WhatsApp-related information for the company.
    """
    try:
        # Get company from current user ID
        from app.contexts.company_profile.service import CompanyProfileService
        company_service = CompanyProfileService()
        companies = await company_service.get_companies()
        company = None
        for comp in companies:
            if hasattr(comp, 'user_id') and comp.user_id == user_id:
                company = comp
                break
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found for user"
            )

        # Validate company ID - users can only check their own status
        # For testing, allow admin to check any company
        if user_id != "admin" and company.id != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access WhatsApp status for other companies"
            )

        service = WhatsAppGatewayService()
        status_response = await service.get_opt_status(company_id)

        if not status_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="WhatsApp status not found for company"
            )

        logger.info(
            "whatsapp_status_retrieved",
            company_id=company_id,
            is_opted_in=status_response.is_opted_in,
            requested_by=current_user["id"],
        )

        return BaseResponse(
            data=status_response,
            message="WhatsApp status retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_whatsapp_status_error",
            error=str(e),
            company_id=company_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve WhatsApp status"
        )


@router.get("/stats")
async def get_whatsapp_stats(
    user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[WhatsAppStatsResponse]:
    """
    Get WhatsApp gateway statistics.
    
    Returns overall statistics for the WhatsApp gateway including
    opt-in rates, message delivery rates, and usage metrics.
    Only accessible to admin users.
    """
    try:
        # Validate admin permissions
        if user_id != "admin":  # Simplified check for testing
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can access WhatsApp statistics"
            )

        service = WhatsAppGatewayService()
        stats_response = await service.get_whatsapp_stats()

        logger.info(
            "whatsapp_stats_retrieved",
            total_companies=stats_response.total_companies,
            opted_in_companies=stats_response.opted_in_companies,
            total_messages_sent=stats_response.total_messages_sent,
            requested_by=current_user["id"],
        )

        return BaseResponse(
            data=stats_response,
            message="WhatsApp statistics retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_whatsapp_stats_error",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve WhatsApp statistics"
        )


@router.post("/test")
async def test_whatsapp_connection(
    user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id)
) -> BaseResponse[dict[str, Any]]:
    """
    Test WhatsApp gateway connection.
    
    Sends a test message to verify WhatsApp integration
    is working correctly. Only accessible to admin users.
    """
    try:
        # Validate admin permissions
        if user_id != "admin":  # Simplified check for testing
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can test WhatsApp connection"
            )

        # Get company for test message
        from app.contexts.company_profile.service import CompanyProfileService
        company_service = CompanyProfileService()
        companies = await company_service.get_companies()
        company = None
        for comp in companies:
            if hasattr(comp, 'user_id') and comp.user_id == user_id:
                company = comp
                break
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found for user"
            )

        # Send test message
        task_result = send_whatsapp_alert.delay(
            company_id=company.id,
            message_type="test",
            content="🧪 *Test Message*\n\nThis is a test message from Tender Copilot WhatsApp gateway.\n\nIf you received this, the integration is working correctly!",
        )

        logger.info(
            "whatsapp_test_message_queued",
            company_id=company.id,
            task_id=task_result.id,
            requested_by=current_user["id"],
        )

        return BaseResponse(
            data={
                "task_id": task_result.id,
                "status": "queued",
                "message": "Test message queued successfully",
            },
            message="WhatsApp connection test initiated"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "test_whatsapp_connection_error",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test WhatsApp connection"
        )
