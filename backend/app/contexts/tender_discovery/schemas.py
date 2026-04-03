from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.contexts.tender_discovery.models import (
    TenderCategory,
    TenderPriority,
    TenderSource,
    TenderStatus,
)


# Request/Response Schemas
class TenderResponse(BaseModel):
    """Tender response schema."""
    id: UUID
    company_id: UUID
    tender_id: str
    title: str
    description: str
    source: TenderSource
    source_url: str
    reference_number: str | None
    category: TenderCategory
    subcategory: str | None
    priority: TenderPriority
    estimated_value: float | None
    emd_amount: float | None
    processing_fee: float | None
    published_date: datetime
    bid_submission_deadline: datetime
    bid_opening_date: datetime | None
    tender_validity: datetime | None
    completion_period: int | None
    status: TenderStatus
    is_active: bool
    is_bookmarked: bool
    state: str | None
    district: str | None
    pin_code: str | None
    procuring_entity: str
    procuring_entity_type: str | None
    eligibility_criteria: str | None
    document_requirements: str | None
    terms_and_conditions: str | None
    contact_person: str | None
    contact_phone: str | None
    contact_email: str | None
    scraped_at: datetime
    last_updated: datetime
    raw_data: dict | None

    # Computed properties
    is_bid_submission_open: bool = False
    days_until_deadline: int = 0
    is_urgent: bool = False
    is_closing_soon: bool = False

    model_config = ConfigDict(from_attributes=True)


class TenderCreate(BaseModel):
    """Tender creation schema."""
    company_id: UUID
    tender_id: str
    title: str
    description: str
    source: TenderSource
    source_url: str
    reference_number: str | None = None
    category: TenderCategory
    subcategory: str | None = None
    priority: TenderPriority = TenderPriority.MEDIUM
    estimated_value: float | None = None
    emd_amount: float | None = None
    processing_fee: float | None = None
    published_date: datetime
    bid_submission_deadline: datetime
    bid_opening_date: datetime | None = None
    tender_validity: datetime | None = None
    completion_period: int | None = None
    status: TenderStatus = TenderStatus.PUBLISHED
    is_active: bool = True
    is_bookmarked: bool = False
    state: str | None = None
    district: str | None = None
    pin_code: str | None = None
    procuring_entity: str
    procuring_entity_type: str | None = None
    eligibility_criteria: str | None = None
    document_requirements: str | None = None
    terms_and_conditions: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    raw_data: dict | None = None

    @field_validator('bid_submission_deadline')
    @classmethod
    def validate_deadline_future(cls, v):
        if v and v <= datetime.now(UTC):
            raise ValueError('Bid submission deadline must be in the future')
        return v

    @field_validator('estimated_value', 'emd_amount', 'processing_fee')
    @classmethod
    def validate_positive_amounts(cls, v):
        if v is not None and v < 0:
            raise ValueError('Amounts must be positive')
        return v


class TenderUpdate(BaseModel):
    """Tender update schema."""
    title: str | None = None
    description: str | None = None
    category: TenderCategory | None = None
    subcategory: str | None = None
    priority: TenderPriority | None = None
    estimated_value: float | None = None
    emd_amount: float | None = None
    processing_fee: float | None = None
    bid_submission_deadline: datetime | None = None
    bid_opening_date: datetime | None = None
    tender_validity: datetime | None = None
    completion_period: int | None = None
    status: TenderStatus | None = None
    is_active: bool | None = None
    is_bookmarked: bool | None = None
    state: str | None = None
    district: str | None = None
    pin_code: str | None = None
    procuring_entity: str | None = None
    procuring_entity_type: str | None = None
    eligibility_criteria: str | None = None
    document_requirements: str | None = None
    terms_and_conditions: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    raw_data: dict | None = None


class TenderSearchFilters(BaseModel):
    """Tender search filters."""
    search_query: str | None = None
    category: TenderCategory | None = None
    min_value: float | None = None
    max_value: float | None = None
    state: str | None = None
    source: TenderSource | None = None
    status: TenderStatus | None = None
    priority: TenderPriority | None = None
    is_bookmarked: bool | None = None
    is_active: bool | None = None
    deadline_days: int | None = None  # Tenders closing within X days
    date_from: datetime | None = None
    date_to: datetime | None = None

    @field_validator('min_value', 'max_value')
    @classmethod
    def validate_value_range(cls, v):
        if v is not None and v < 0:
            raise ValueError('Values must be positive')
        return v

    @field_validator('deadline_days')
    @classmethod
    def validate_deadline_days(cls, v):
        if v is not None and v < 0:
            raise ValueError('Deadline days must be positive')
        return v


class TenderListResponse(BaseModel):
    """Tender list response."""
    tenders: list[TenderResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


class TenderStatsResponse(BaseModel):
    """Tender statistics response."""
    total_tenders: int
    active_tenders: int
    bookmarked_tenders: int
    closing_soon: int  # Closing within 7 days
    urgent: int  # Closing within 3 days
    by_category: dict[str, int]
    by_source: dict[str, int]
    by_status: dict[str, int]
    total_estimated_value: float | None


# Search Schemas
class TenderSearchResponse(BaseModel):
    """Tender search response."""
    id: UUID
    company_id: UUID
    search_query: str | None
    category: TenderCategory | None
    min_value: float | None
    max_value: float | None
    state: str | None
    source: TenderSource | None
    is_saved_search: bool
    search_name: str | None
    alert_enabled: bool
    created_at: datetime
    last_run: datetime | None
    run_count: int

    model_config = ConfigDict(from_attributes=True)


class TenderSearchCreate(BaseModel):
    """Tender search creation schema."""
    search_query: str | None = None
    category: TenderCategory | None = None
    min_value: float | None = None
    max_value: float | None = None
    state: str | None = None
    source: TenderSource | None = None
    is_saved_search: bool = False
    search_name: str | None = None
    alert_enabled: bool = False


class TenderSearchUpdate(BaseModel):
    """Tender search update schema."""
    search_query: str | None = None
    category: TenderCategory | None = None
    min_value: float | None = None
    max_value: float | None = None
    state: str | None = None
    source: TenderSource | None = None
    is_saved_search: bool | None = None
    search_name: str | None = None
    alert_enabled: bool | None = None


# Alert Schemas
class TenderAlertResponse(BaseModel):
    """Tender alert response."""
    id: UUID
    company_id: UUID
    tender_id: UUID
    alert_type: str
    message: str
    is_read: bool
    is_sent: bool
    sent_via_email: bool
    sent_via_whatsapp: bool
    created_at: datetime
    sent_at: datetime | None
    read_at: datetime | None

    # Include tender details
    tender: TenderResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class TenderAlertCreate(BaseModel):
    """Tender alert creation schema."""
    tender_id: UUID
    alert_type: str
    message: str


class TenderAlertUpdate(BaseModel):
    """Tender alert update schema."""
    is_read: bool | None = None


# Classification Schemas
class TenderClassificationRequest(BaseModel):
    """Tender classification request."""
    title: str
    description: str
    procuring_entity: str
    estimated_value: float | None = None


class TenderClassificationResponse(BaseModel):
    """Tender classification response."""
    category: TenderCategory
    subcategory: str | None
    priority: TenderPriority
    confidence: float
    reasoning: str


# Scraping Schemas
class ScrapingJobCreate(BaseModel):
    """Scraping job creation schema."""
    source: TenderSource
    state: str | None = None
    category: TenderCategory | None = None
    keywords: list[str] | None = None


class ScrapingJobResponse(BaseModel):
    """Scraping job response."""
    job_id: str
    source: TenderSource
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    tenders_found: int
    tenders_created: int
    errors: list[str]


# Bulk Operations
class TenderBulkUpdate(BaseModel):
    """Bulk tender update schema."""
    tender_ids: list[UUID]
    updates: TenderUpdate


class TenderBulkDelete(BaseModel):
    """Bulk tender delete schema."""
    tender_ids: list[UUID]
    confirm: bool = False

    @field_validator('confirm')
    @classmethod
    def validate_confirmation(cls, v):
        if not v:
            raise ValueError('Must confirm bulk deletion')
        return v


# Export Schemas
class TenderExportRequest(BaseModel):
    """Tender export request."""
    format: str = "csv"  # csv, xlsx, json
    filters: TenderSearchFilters | None = None
    include_raw_data: bool = False


class TenderExportResponse(BaseModel):
    """Tender export response."""
    export_id: str
    format: str
    status: str
    download_url: str | None
    created_at: datetime
    completed_at: datetime | None
    record_count: int | None
