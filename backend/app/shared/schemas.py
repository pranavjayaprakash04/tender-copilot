from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    """Base response envelope for all API responses."""
    data: T
    success: bool = True
    message: str | None = None
    trace_id: str | None = None
    timestamp: datetime

    def __init__(self, **data):
        data["timestamp"] = datetime.utcnow()
        super().__init__(**data)

class PaginatedResponse(BaseResponse[list[T]], Generic[T]):
    """Paginated response for list endpoints."""
    pagination: PaginationMeta

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool

class ErrorResponse(BaseModel):
    """Error response envelope."""
    error: ErrorDetail
    success: bool = False
    trace_id: str
    timestamp: datetime

    def __init__(self, **data):
        data["timestamp"] = datetime.utcnow()
        super().__init__(**data)

class ErrorDetail(BaseModel):
    """Error detail information."""
    code: str
    message: str
    detail: Any | None = None
