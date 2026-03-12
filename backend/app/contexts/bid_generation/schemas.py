"""Bid generation schemas."""

from __future__ import annotations

from uuid import UUID
from typing import Any
from pydantic import BaseModel, Field

from app.contexts.bid_generation.models import BidType


class BidGenerationCreate(BaseModel):
    """Schema for creating bid generation."""
    tender_id: UUID
    bid_type: BidType
    language: str = "en"
    bid_title: str
    bid_description: str | None = None
    task_id: str
    template_id: str | None = None
    customization_applied: bool = False