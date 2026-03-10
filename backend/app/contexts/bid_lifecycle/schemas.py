from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, validator

from app.contexts.bid_lifecycle.models import (
    BidOutcome,
    BidStatus,
    LossReason,
    PaymentStatus,
)


# Request/Response Schemas
class BidResponse(BaseModel):
    """Bid response schema."""
    id: UUID
    company_id: UUID
    tender_id: UUID
    bid_number: str
    title: str
    description: str | None
    bid_amount: float
    emd_amount: float | None
    bid_security_amount: float | None
    submission_deadline: datetime
    submission_date: datetime | None
    evaluation_start_date: datetime | None
    award_date: datetime | None
    status: BidStatus
    previous_status: BidStatus | None
    lead_bidder: str | None
    bid_manager: str | None
    technical_lead: str | None
    compliance_score: float | None
    technical_score: float | None
    financial_score: float | None
    notes: str | None
    internal_notes: str | None
    tags: dict | None
    created_at: datetime
    updated_at: datetime

    # Computed properties
    can_edit: bool = False
    can_submit: bool = False
    can_withdraw: bool = False
    is_final_status: bool = False
    days_since_submission: int | None
    is_overdue_payment: bool = False

    class Config:
        from_attributes = True


class BidCreate(BaseModel):
    """Bid creation schema."""
    company_id: UUID
    tender_id: UUID
    bid_number: str
    title: str
    description: str | None = None
    bid_amount: float
    emd_amount: float | None = None
    bid_security_amount: float | None = None
    submission_deadline: datetime
    lead_bidder: str | None = None
    bid_manager: str | None = None
    technical_lead: str | None = None
    compliance_score: float | None = None
    technical_score: float | None = None
    financial_score: float | None = None
    notes: str | None = None
    internal_notes: str | None = None
    tags: dict | None = None

    @validator('bid_amount', 'emd_amount', 'bid_security_amount')
    def validate_positive_amounts(cls, v):
        if v is not None and v < 0:
            raise ValueError('Amounts must be positive')
        return v

    @validator('submission_deadline')
    def validate_deadline_future(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Submission deadline must be in the future')
        return v


class BidUpdate(BaseModel):
    """Bid update schema."""
    title: str | None = None
    description: str | None = None
    bid_amount: float | None = None
    emd_amount: float | None = None
    bid_security_amount: float | None = None
    submission_deadline: datetime | None = None
    lead_bidder: str | None = None
    bid_manager: str | None = None
    technical_lead: str | None = None
    compliance_score: float | None = None
    technical_score: float | None = None
    financial_score: float | None = None
    notes: str | None = None
    internal_notes: str | None = None
    tags: dict | None = None


class BidStatusTransition(BaseModel):
    """Bid status transition schema."""
    new_status: BidStatus
    reason: str | None = None
    internal_notes: str | None = None


class BidSearchFilters(BaseModel):
    """Bid search filters."""
    search_query: str | None = None
    status: BidStatus | None = None
    tender_id: UUID | None = None
    lead_bidder: str | None = None
    bid_manager: str | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    submission_date_from: datetime | None = None
    submission_date_to: datetime | None = None
    deadline_from: datetime | None = None
    deadline_to: datetime | None = None
    is_editable: bool | None = None
    is_submittable: bool | None = None
    has_overdue_payments: bool | None = None


class BidListResponse(BaseModel):
    """Bid list response."""
    bids: list[BidResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


class BidStatsResponse(BaseModel):
    """Bid statistics response."""
    total_bids: int
    draft_bids: int
    reviewing_bids: int
    submitted_bids: int
    under_evaluation_bids: int
    awarded_bids: int
    won_bids: int
    lost_bids: int
    withdrawn_bids: int
    disqualified_bids: int
    total_bid_value: float
    won_bid_value: float
    win_rate: float
    average_bid_amount: float
    submissions_this_month: int
    wins_this_month: int


# Outcome Schemas
class BidOutcomeRecordResponse(BaseModel):
    """Bid outcome record response."""
    id: UUID
    bid_id: UUID
    outcome: BidOutcome
    loss_reason: LossReason | None
    loss_reason_details: str | None
    winning_bidder: str | None
    winning_amount: float | None
    competitor_count: int | None
    our_ranking: int | None
    technical_score_received: float | None
    financial_score_received: float | None
    total_score_received: float | None
    max_possible_score: float | None
    evaluation_feedback: str | None
    strengths: str | None
    weaknesses: str | None
    improvement_recommendations: str | None
    profit_margin: float | None
    cost_breakdown: dict | None
    pricing_strategy: str | None
    recorded_by: str | None
    verified: bool
    verified_by: str | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BidOutcomeRecordCreate(BaseModel):
    """Bid outcome record creation schema."""
    bid_id: UUID
    outcome: BidOutcome
    loss_reason: LossReason | None = None
    loss_reason_details: str | None = None
    winning_bidder: str | None = None
    winning_amount: float | None = None
    competitor_count: int | None = None
    our_ranking: int | None = None
    technical_score_received: float | None = None
    financial_score_received: float | None = None
    total_score_received: float | None = None
    max_possible_score: float | None = None
    evaluation_feedback: str | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    improvement_recommendations: str | None = None
    profit_margin: float | None = None
    cost_breakdown: dict | None = None
    pricing_strategy: str | None = None
    recorded_by: str | None = None


class BidOutcomeRecordUpdate(BaseModel):
    """Bid outcome record update schema."""
    loss_reason: LossReason | None = None
    loss_reason_details: str | None = None
    winning_bidder: str | None = None
    winning_amount: float | None = None
    competitor_count: int | None = None
    our_ranking: int | None = None
    technical_score_received: float | None = None
    financial_score_received: float | None = None
    total_score_received: float | None = None
    max_possible_score: float | None = None
    evaluation_feedback: str | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    improvement_recommendations: str | None = None
    profit_margin: float | None = None
    cost_breakdown: dict | None = None
    pricing_strategy: str | None = None
    verified: bool | None = None
    verified_by: str | None = None


# Payment Schemas
class BidPaymentResponse(BaseModel):
    """Bid payment response."""
    id: UUID
    bid_id: UUID
    payment_type: str
    payment_amount: float
    due_date: datetime
    status: PaymentStatus
    paid_amount: float | None
    paid_date: datetime | None
    invoice_number: str | None
    invoice_date: datetime | None
    payment_terms: str | None
    last_follow_up_date: datetime | None
    follow_up_count: int
    next_follow_up_date: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Computed properties
    is_overdue: bool = False
    days_overdue: int = 0
    outstanding_amount: float = 0.0

    class Config:
        from_attributes = True


class BidPaymentCreate(BaseModel):
    """Bid payment creation schema."""
    bid_id: UUID
    payment_type: str
    payment_amount: float
    due_date: datetime
    invoice_number: str | None = None
    invoice_date: datetime | None = None
    payment_terms: str | None = None
    notes: str | None = None

    @validator('payment_amount')
    def validate_positive_amount(cls, v):
        if v <= 0:
            raise ValueError('Payment amount must be positive')
        return v


class BidPaymentUpdate(BaseModel):
    """Bid payment update schema."""
    status: PaymentStatus | None = None
    paid_amount: float | None = None
    paid_date: datetime | None = None
    invoice_number: str | None = None
    invoice_date: datetime | None = None
    payment_terms: str | None = None
    notes: str | None = None


# Follow-up Schemas
class BidFollowUpResponse(BaseModel):
    """Bid follow-up response."""
    id: UUID
    bid_id: UUID
    payment_id: UUID | None
    follow_up_type: str
    priority: str
    contact_person: str | None
    contact_method: str
    status: str
    scheduled_date: datetime
    completed_date: datetime | None
    subject: str
    message: str
    response: str | None
    assigned_to: str | None
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime

    # Computed properties
    is_overdue: bool = False
    days_overdue: int = 0

    class Config:
        from_attributes = True


class BidFollowUpCreate(BaseModel):
    """Bid follow-up creation schema."""
    bid_id: UUID
    payment_id: UUID | None = None
    follow_up_type: str
    priority: str = "medium"
    contact_person: str | None = None
    contact_method: str
    scheduled_date: datetime
    subject: str
    message: str
    assigned_to: str | None = None


class BidFollowUpUpdate(BaseModel):
    """Bid follow-up update schema."""
    status: str | None = None
    completed_date: datetime | None = None
    response: str | None = None
    assigned_to: str | None = None
    reminder_sent: bool | None = None


# Analysis Schemas
class LossAnalysisRequest(BaseModel):
    """Loss analysis request."""
    bid_id: UUID
    include_competitor_analysis: bool = True
    include_pricing_analysis: bool = True
    include_technical_analysis: bool = True


class LossAnalysisResponse(BaseModel):
    """Loss analysis response."""
    bid_id: UUID
    analysis_summary: str
    key_factors: list[str]
    recommendations: list[str]
    competitor_insights: dict | None
    pricing_insights: dict | None
    technical_insights: dict | None
    confidence_score: float
    generated_at: datetime


class PaymentFollowUpRequest(BaseModel):
    """Payment follow-up request."""
    days_overdue: int = 30
    include_overdue_only: bool = True
    send_notifications: bool = False


class PaymentFollowUpResponse(BaseModel):
    """Payment follow-up response."""
    payments_processed: int
    follow_ups_created: int
    notifications_sent: int
    processed_payment_ids: list[UUID]


# Bulk Operations
class BidBulkUpdate(BaseModel):
    """Bulk bid update schema."""
    bid_ids: list[UUID]
    updates: BidUpdate


class BidBulkStatusTransition(BaseModel):
    """Bulk bid status transition schema."""
    bid_ids: list[UUID]
    new_status: BidStatus
    reason: str | None = None
    internal_notes: str | None = None


# Export Schemas
class BidExportRequest(BaseModel):
    """Bid export request."""
    format: str = "csv"  # csv, xlsx, json
    filters: BidSearchFilters | None = None
    include_outcomes: bool = False
    include_payments: bool = False
    include_follow_ups: bool = False


class BidExportResponse(BaseModel):
    """Bid export response."""
    export_id: str
    format: str
    status: str
    download_url: str | None
    created_at: datetime
    completed_at: datetime | None
    record_count: int | None
