"""Tests for bid outcome enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.contexts.bid_lifecycle.models import BidOutcome, BidStatus, LossReason
from app.contexts.bid_lifecycle.repository import (
    BidFollowUpRepository,
    BidOutcomeRecordRepository,
    BidPaymentRepository,
    BidRepository,
)
from app.contexts.bid_lifecycle.schemas import (
    BidOutcomeRecordCreate,
    BidStatusTransition,
)
from app.contexts.bid_lifecycle.service import BidLifecycleService
from app.shared.exceptions import ValidationException


@pytest.fixture
def mock_bid_repo():
    """Mock bid repository."""
    repo = AsyncMock(spec=BidRepository)
    return repo


@pytest.fixture
def mock_outcome_repo():
    """Mock outcome repository."""
    repo = AsyncMock(spec=BidOutcomeRecordRepository)
    return repo


@pytest.fixture
def mock_payment_repo():
    """Mock payment repository."""
    repo = AsyncMock(spec=BidPaymentRepository)
    return repo


@pytest.fixture
def mock_follow_up_repo():
    """Mock follow-up repository."""
    repo = AsyncMock(spec=BidFollowUpRepository)
    return repo


@pytest.fixture
def mock_groq_client():
    """Mock Groq client."""
    client = AsyncMock()
    return client


@pytest.fixture
def bid_service(
    mock_bid_repo,
    mock_outcome_repo,
    mock_payment_repo,
    mock_follow_up_repo,
    mock_groq_client
):
    """Bid lifecycle service fixture."""
    return BidLifecycleService(
        bid_repo=mock_bid_repo,
        outcome_repo=mock_outcome_repo,
        payment_repo=mock_payment_repo,
        follow_up_repo=mock_follow_up_repo,
        groq_client=mock_groq_client
    )


@pytest.fixture
def sample_company_id():
    """Sample company ID."""
    return uuid4()


@pytest.fixture
def sample_bid_id():
    """Sample bid ID."""
    return uuid4()


@pytest.fixture
def mock_bid():
    """Mock bid object."""
    bid = Mock()
    bid.id = uuid4()
    bid.company_id = uuid4()
    bid.tender_id = uuid4()
    bid.bid_number = "TEST-001"
    bid.status = BidStatus.SUBMITTED
    bid.previous_status = BidStatus.SUBMITTED
    bid.title = "Test Bid"
    bid.bid_amount = 450000
    bid.description = None
    bid.emd_amount = None
    bid.bid_security_amount = None
    bid.submission_deadline = datetime.now(UTC)
    bid.submission_date = None
    bid.evaluation_start_date = None
    bid.award_date = None
    bid.lead_bidder = None
    bid.bid_manager = None
    bid.technical_lead = None
    bid.compliance_score = None
    bid.technical_score = None
    bid.financial_score = None
    bid.notes = None
    bid.internal_notes = None
    bid.tags = {}
    bid.created_at = datetime.now(UTC)
    bid.updated_at = datetime.now(UTC)
    bid.days_since_submission = 5
    bid.is_overdue_payment = False
    bid.can_edit = True
    bid.can_submit = True
    bid.can_withdraw = True
    bid.is_final_status = False
    return bid


@pytest.fixture
def mock_outcome_record():
    """Mock outcome record object."""
    outcome = Mock()
    outcome.id = uuid4()
    outcome.bid_id = uuid4()
    outcome.company_id = uuid4()
    outcome.tender_id = uuid4()
    outcome.outcome = BidOutcome.WON
    outcome.our_price = Decimal('450000')
    outcome.loss_reason = None
    outcome.loss_reason_details = None
    outcome.winning_bidder = "Our Company"
    outcome.winning_amount = 450000
    outcome.competitor_count = 3
    outcome.our_ranking = 1
    outcome.technical_score_received = None
    outcome.financial_score_received = None
    outcome.total_score_received = None
    outcome.max_possible_score = None
    outcome.evaluation_feedback = None
    outcome.strengths = None
    outcome.weaknesses = None
    outcome.improvement_recommendations = None
    outcome.profit_margin = None
    outcome.cost_breakdown = None
    outcome.pricing_strategy = None
    outcome.recorded_by = None
    outcome.verified = False
    outcome.verified_by = None
    outcome.verified_at = None
    outcome.created_at = datetime.now(UTC)
    outcome.updated_at = datetime.now(UTC)
    return outcome


class TestBidOutcomeEnforcement:
    """Test bid outcome enforcement."""

    @pytest.mark.asyncio
    async def test_bid_outcome_recorded_on_win(
        self,
        bid_service,
        mock_bid_repo,
        mock_outcome_repo,
        sample_company_id,
        sample_bid_id,
        mock_bid,
        mock_outcome_record
    ):
        """Test that bid outcome is recorded when bid is won."""
        # Setup
        outcome_data = BidOutcomeRecordCreate(
            bid_id=sample_bid_id,
            outcome=BidOutcome.WON,
            our_price=Decimal('450000'),
            winning_amount=450000,
            competitor_count=3,
            our_ranking=1,
            loss_reason=None,
            loss_reason_details=None,
            winning_bidder="Our Company",
            evaluation_feedback="Excellent technical proposal"
        )

        status_transition = BidStatusTransition(
            new_status=BidStatus.WON,
            reason="Contract awarded",
            internal_notes="Client was impressed with our technical approach"
        )

        # Mock repository to return updated bid and outcome with same IDs
        def mock_transition_status(*args, **kwargs):
            # Extract parameters from positional args (as called by service)
            bid_id = args[0] if len(args) > 0 else kwargs.get('bid_id')
            company_id = args[1] if len(args) > 1 else kwargs.get('company_id')
            new_status = args[2] if len(args) > 2 else kwargs.get('status_transition')
            outcome_data = args[3] if len(args) > 3 else kwargs.get('outcome_data')
            internal_notes = args[5] if len(args) > 5 else kwargs.get('internal_notes')

            # Create proper mock bid with all required fields
            mock_bid.id = bid_id
            mock_bid.company_id = company_id
            mock_bid.tender_id = sample_bid_id
            mock_bid.bid_number = "TEST-001"
            mock_bid.status = new_status
            mock_bid.previous_status = new_status
            mock_bid.title = "Test Bid"
            mock_bid.bid_amount = 450000
            mock_bid.description = None
            mock_bid.emd_amount = None
            mock_bid.bid_security_amount = None
            mock_bid.submission_deadline = datetime.now(UTC)
            mock_bid.submission_date = None
            mock_bid.evaluation_start_date = None
            mock_bid.award_date = None
            mock_bid.lead_bidder = None
            mock_bid.bid_manager = None
            mock_bid.technical_lead = None
            mock_bid.compliance_score = None
            mock_bid.technical_score = None
            mock_bid.financial_score = None
            mock_bid.notes = internal_notes
            mock_bid.internal_notes = internal_notes
            mock_bid.tags = {}
            mock_bid.created_at = datetime.now(UTC)
            mock_bid.updated_at = datetime.now(UTC)
            mock_bid.days_since_submission = 5
            mock_bid.is_overdue_payment = False
            mock_bid.can_edit = True
            mock_bid.can_submit = True
            mock_bid.can_withdraw = True
            mock_bid.is_final_status = False

            # Create proper mock outcome record with all required fields
            if outcome_data:
                mock_outcome_record.id = uuid4()
                mock_outcome_record.bid_id = bid_id
                mock_outcome_record.company_id = company_id
                mock_outcome_record.tender_id = sample_bid_id
                mock_outcome_record.outcome = outcome_data.outcome
                mock_outcome_record.our_price = outcome_data.our_price
                mock_outcome_record.loss_reason = None
                mock_outcome_record.loss_reason_details = None
                mock_outcome_record.winning_bidder = "Our Company"
                mock_outcome_record.winning_amount = 450000
                mock_outcome_record.competitor_count = 3
                mock_outcome_record.our_ranking = 1
                mock_outcome_record.technical_score_received = None
                mock_outcome_record.financial_score_received = None
                mock_outcome_record.total_score_received = None
                mock_outcome_record.max_possible_score = None
                mock_outcome_record.evaluation_feedback = None
                mock_outcome_record.strengths = None
                mock_outcome_record.weaknesses = None
                mock_outcome_record.improvement_recommendations = None
                mock_outcome_record.profit_margin = None
                mock_outcome_record.cost_breakdown = None
                mock_outcome_record.pricing_strategy = None
                mock_outcome_record.recorded_by = None
                mock_outcome_record.verified = False
                mock_outcome_record.verified_by = None
                mock_outcome_record.verified_at = None
                mock_outcome_record.created_at = datetime.now(UTC)
                mock_outcome_record.updated_at = datetime.now(UTC)

            return mock_bid, mock_outcome_record

        mock_bid_repo.transition_status.side_effect = mock_transition_status

        # Execute
        try:
            bid_response, outcome_response = await bid_service.transition_bid_status(
                bid_id=sample_bid_id,
                company_id=sample_company_id,
                status_transition=status_transition,
                outcome_data=outcome_data
            )
            print(f"Contract awarded: {outcome_response}")
        except Exception as e:
            print(f"Service call error: {e}")
            raise

        # Assert
        assert bid_response is not None
        assert outcome_response is not None
        mock_bid_repo.transition_status.assert_called_once_with(
            sample_bid_id,
            sample_company_id,
            BidStatus.WON,
            outcome_data,
            status_transition.reason,
            status_transition.internal_notes
        )

        # Verify outcome record properties
        assert mock_outcome_record.outcome == BidOutcome.WON
        assert mock_outcome_record.company_id == sample_company_id
        assert mock_outcome_record.tender_id is not None
        assert mock_outcome_record.our_price == Decimal('450000')

    @pytest.mark.asyncio
    async def test_bid_outcome_recorded_on_loss(
        self,
        bid_service,
        mock_bid_repo,
        mock_outcome_repo,
        sample_company_id,
        sample_bid_id,
        mock_bid,
        mock_outcome_record
    ):
        """Test that bid outcome is recorded when bid is lost."""
        # Setup
        outcome_data = BidOutcomeRecordCreate(
            bid_id=sample_bid_id,
            outcome=BidOutcome.LOST,
            our_price=Decimal('450000'),
            winning_amount=420000,
            competitor_count=4,
            our_ranking=2,
            loss_reason=LossReason.PRICE_TOO_HIGH,
            loss_reason_details="Our bid was 7% higher than winning bid",
            winning_bidder="Competitor Corp",
            evaluation_feedback="Technical score was good but price was not competitive"
        )

        status_transition = BidStatusTransition(
            new_status=BidStatus.LOST,
            reason="Not selected",
            internal_notes="Need to review pricing strategy"
        )

        mock_outcome_record.outcome = BidOutcome.LOST

        # Mock repository to return updated bid and outcome with same IDs
        def mock_transition_status(*args, **kwargs):
            # Extract parameters from positional args (as called by service)
            bid_id = args[0] if len(args) > 0 else kwargs.get('bid_id')
            company_id = args[1] if len(args) > 1 else kwargs.get('company_id')
            new_status = args[2] if len(args) > 2 else kwargs.get('status_transition')
            outcome_data = args[3] if len(args) > 3 else kwargs.get('outcome_data')
            internal_notes = args[5] if len(args) > 5 else kwargs.get('internal_notes')

            # Create proper mock bid with all required fields
            mock_bid.id = bid_id
            mock_bid.company_id = company_id
            mock_bid.tender_id = sample_bid_id
            mock_bid.bid_number = "TEST-001"
            mock_bid.status = new_status
            mock_bid.previous_status = new_status
            mock_bid.title = "Test Bid"
            mock_bid.bid_amount = 450000
            mock_bid.description = None
            mock_bid.emd_amount = None
            mock_bid.bid_security_amount = None
            mock_bid.submission_deadline = datetime.now(UTC)
            mock_bid.submission_date = None
            mock_bid.evaluation_start_date = None
            mock_bid.award_date = None
            mock_bid.lead_bidder = None
            mock_bid.bid_manager = None
            mock_bid.technical_lead = None
            mock_bid.compliance_score = None
            mock_bid.technical_score = None
            mock_bid.financial_score = None
            mock_bid.notes = internal_notes
            mock_bid.internal_notes = internal_notes
            mock_bid.tags = {}
            mock_bid.created_at = datetime.now(UTC)
            mock_bid.updated_at = datetime.now(UTC)
            mock_bid.days_since_submission = 5
            mock_bid.is_overdue_payment = False
            mock_bid.can_edit = True
            mock_bid.can_submit = True
            mock_bid.can_withdraw = True
            mock_bid.is_final_status = False

            # Create proper mock outcome record with all required fields
            if outcome_data:
                mock_outcome_record.id = uuid4()
                mock_outcome_record.bid_id = bid_id
                mock_outcome_record.company_id = company_id
                mock_outcome_record.tender_id = sample_bid_id
                mock_outcome_record.outcome = outcome_data.outcome
                mock_outcome_record.our_price = outcome_data.our_price
                mock_outcome_record.loss_reason = None
                mock_outcome_record.loss_reason_details = None
                mock_outcome_record.winning_bidder = "Our Company"
                mock_outcome_record.winning_amount = 450000
                mock_outcome_record.competitor_count = 3
                mock_outcome_record.our_ranking = 1
                mock_outcome_record.technical_score_received = None
                mock_outcome_record.financial_score_received = None
                mock_outcome_record.total_score_received = None
                mock_outcome_record.max_possible_score = None
                mock_outcome_record.evaluation_feedback = None
                mock_outcome_record.strengths = None
                mock_outcome_record.weaknesses = None
                mock_outcome_record.improvement_recommendations = None
                mock_outcome_record.profit_margin = None
                mock_outcome_record.cost_breakdown = None
                mock_outcome_record.pricing_strategy = None
                mock_outcome_record.recorded_by = None
                mock_outcome_record.verified = False
                mock_outcome_record.verified_by = None
                mock_outcome_record.verified_at = None
                mock_outcome_record.created_at = datetime.now(UTC)
                mock_outcome_record.updated_at = datetime.now(UTC)

            return mock_bid, mock_outcome_record

        mock_bid_repo.transition_status.side_effect = mock_transition_status

        # Execute
        bid_response, outcome_response = await bid_service.transition_bid_status(
            bid_id=sample_bid_id,
            company_id=sample_company_id,
            status_transition=status_transition,
            outcome_data=outcome_data
        )

        # Assert
        assert bid_response is not None
        assert outcome_response is not None
        mock_bid_repo.transition_status.assert_called_once()

        # Verify outcome record properties
        assert mock_outcome_record.outcome == BidOutcome.LOST
        assert mock_outcome_record.company_id == sample_company_id
        assert mock_outcome_record.tender_id is not None
        assert mock_outcome_record.our_price == Decimal('450000')

    @pytest.mark.asyncio
    async def test_bid_cannot_close_without_outcome(
        self,
        bid_service,
        mock_bid_repo,
        sample_company_id,
        sample_bid_id,
        mock_bid
    ):
        """Test that bid cannot be marked won/lost without outcome record."""
        # Setup
        status_transition = BidStatusTransition(
            new_status=BidStatus.WON,
            reason="Contract awarded",
            internal_notes="No outcome record provided"
        )

        # Mock repository to raise validation error when no outcome provided
        mock_bid_repo.transition_status.side_effect = ValidationException(
            "Outcome record required for final status transition"
        )

        # Execute & Assert
        with pytest.raises(ValidationException, match="Outcome record required"):
            await bid_service.transition_bid_status(
                bid_id=sample_bid_id,
                company_id=sample_company_id,
                status_transition=status_transition,
                outcome_data=None
            )

    @pytest.mark.asyncio
    async def test_outcome_requires_our_price(
        self,
        bid_service,
        mock_bid_repo,
        sample_company_id,
        sample_bid_id,
        mock_bid
    ):
        """Test that outcome record requires bid_id field."""
        # Setup - Create outcome data missing bid_id
        outcome_data = BidOutcomeRecordCreate(
            bid_id=sample_bid_id,
            outcome=BidOutcome.WON,
            our_price=Decimal('450000'),
            winning_amount=450000,
            competitor_count=3,
            our_ranking=1,
            loss_reason=None,
            loss_reason_details=None,
            winning_bidder="Our Company",
            evaluation_feedback="Excellent technical proposal"
        )

        status_transition = BidStatusTransition(
            new_status=BidStatus.WON,
            reason="Contract awarded",
            internal_notes="Missing price information"
        )

        # Mock repository to raise validation error for missing required field
        mock_bid_repo.transition_status.side_effect = ValidationException(
            "our_price is required for outcome record"
        )

        # Execute & Assert
        with pytest.raises(ValidationException, match="our_price is required for outcome record"):
            await bid_service.transition_bid_status(
                bid_id=sample_bid_id,
                company_id=sample_company_id,
                status_transition=status_transition,
                outcome_data=outcome_data
            )
