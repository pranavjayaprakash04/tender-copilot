from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WhatsAppMessage(BaseModel):
    """WhatsApp message schema."""
    from_phone: str = Field(..., description="Sender phone number in E.164 format")
    to_phone: str = Field(..., description="Recipient phone number in E.164 format")
    message_id: str = Field(..., description="WhatsApp message ID")
    message_type: str = Field(..., description="Message type: text, image, document, etc.")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional message metadata")

    model_config = ConfigDict(from_attributes=True)


class WhatsAppWebhookEntry(BaseModel):
    """Single entry from WhatsApp webhook payload."""
    id: str = Field(..., description="Entry ID")
    changes: list[dict[str, Any]] = Field(..., description="List of changes")

    model_config = ConfigDict(from_attributes=True)


class WhatsAppWebhookPayload(BaseModel):
    """WhatsApp webhook payload schema."""
    object: str = Field(..., description="Object type, should be 'whatsapp_business_account'")
    entry: list[WhatsAppWebhookEntry] = Field(..., description="List of entries")

    @field_validator('object')
    @classmethod
    def validate_object(cls, v: str) -> str:
        if v != 'whatsapp_business_account':
            raise ValueError('Invalid object type for WhatsApp webhook')
        return v


class WhatsAppWebhookVerification(BaseModel):
    """WhatsApp webhook verification request."""
    hub_mode: str = Field(..., alias="hub.mode", description="Webhook verification mode")
    hub_verify_token: str = Field(..., alias="hub.verify_token", description="Verification token")
    hub_challenge: str = Field(..., alias="hub.challenge", description="Challenge string")

    model_config = ConfigDict(populate_by_name=True)


class WhatsAppOutboundMessage(BaseModel):
    """Outbound WhatsApp message schema."""
    company_id: UUID
    recipient_phone: str = Field(..., description="Recipient phone number in E.164 format")
    message_type: str = Field(..., description="Message type: alert, update, etc.")
    content: str = Field(..., description="Message content")
    media_url: str | None = Field(default=None, description="Optional media URL")
    template_name: str | None = Field(default=None, description="Template name for template messages")
    template_variables: dict[str, Any] | None = Field(default=None, description="Template variables")

    @field_validator('recipient_phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.startswith('+'):
            raise ValueError('Phone number must be in E.164 format starting with +')
        return v


class WhatsAppMessageLog(BaseModel):
    """Logged WhatsApp message."""
    id: UUID
    company_id: UUID
    message_id: str
    direction: str  # inbound, outbound
    from_phone: str
    to_phone: str
    content: str
    message_type: str
    status: str
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    error_message: str | None
    metadata: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)


class WhatsAppOptStatus(BaseModel):
    """WhatsApp opt-in status for a company."""
    company_id: UUID
    phone_number: str
    is_opted_in: bool
    opt_in_date: datetime | None
    opt_out_date: datetime | None
    last_message_date: datetime | None
    message_count: int

    model_config = ConfigDict(from_attributes=True)


class WhatsAppSendRequest(BaseModel):
    """Request to send WhatsApp message."""
    company_id: UUID
    recipient_phone: str
    message_type: str = "alert"
    content: str
    media_url: str | None = None
    template_name: str | None = None
    template_variables: dict[str, Any] | None = None
    priority: str = "normal"  # low, normal, high

    model_config = ConfigDict(from_attributes=True)


class WhatsAppSendResponse(BaseModel):
    """Response after sending WhatsApp message."""
    message_id: str
    status: str
    sent_at: datetime
    error_message: str | None = None


class WhatsAppStatusResponse(BaseModel):
    """WhatsApp status response for a company."""
    company_id: UUID
    phone_number: str
    is_opted_in: bool
    opt_in_date: datetime | None
    opt_out_date: datetime | None
    last_message_date: datetime | None
    total_messages_sent: int
    total_messages_received: int
    last_message_content: str | None

    model_config = ConfigDict(from_attributes=True)


class WhatsAppStatsResponse(BaseModel):
    """WhatsApp statistics response."""
    total_companies: int
    opted_in_companies: int
    opted_out_companies: int
    total_messages_sent: int
    total_messages_delivered: int
    total_messages_failed: int
    delivery_rate: float
    messages_by_type: dict[str, int]
    recent_activity: list[WhatsAppMessageLog]

    model_config = ConfigDict(from_attributes=True)