"""Tests for Bid Lifecycle context."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.contexts.bid_lifecycle.models import (
    BidOutcome,
    BidStatus,
    LossReason,
)
from app.contexts.bid_lifecycle.repository import (
    BidFollowUpRepository,
    BidOutcomeRecordRepository,
    BidPaymentRepository,
    BidRepository,
)
from app.contexts.bid_lifecycle.schemas import (
    BidCreate,
    BidOutcomeRecordCreate,
    BidSearchFilters,
    BidStatusTransition,
    BidUpdate,
)
from app.contexts.bid_lifecycle.service import BidLifecycleService
from app.shared.exceptions import NotFoundException, ValidationException
from tests.conftest import TestDatabase


class TestBidRepository(TestDatabase):
    """Test BidRepository operations."""

    @pytest.fixture
    def bid_repo(self, session):
        return BidRepository(session)

    @pytest.fixture
    def sample_bid_data(self):
        return BidCreate(
            company_id=uuid4(),
            tender_id=uuid4(),
            bid_number="BID-2024-001",
            title="Test Bid",
            description="Test bid description",
            bid_amount=100000.00,
            submission_deadline=datetime.utcnow() + timedelta(days=30)
        )

    async def test_create_bid(self, bid_repo, sample_bid_data):
        """Test bid creation."""
        bid = await bid_repo.create(sample_bid_data)

        assert bid.id is not None
        assert bid.bid_number == sample_bid_data.bid_number
        assert bid.status == BidStatus.DRAFT
        assert bid.can_edit is True
        assert bid.can_submit is True
        assert bid.is_final_status is False

    async def test_create_bid_duplicate_number(self, bid_repo, sample_bid_data):
        """Test creating bid with duplicate number fails."""
        await bid_repo.create(sample_bid_data)

        with pytest.raises(ValidationException, match="Bid number already exists"):
            await bid_repo.create(sample_bid_data)

    async def test_get_bid_by_id(self, bid_repo, sample_bid_data):
        """Test getting bid by ID."""
        created_bid = await bid_repo.create(sample_bid_data)
        retrieved_bid = await bid_repo.get_by_id(created_bid.id, sample_bid_data.company_id)

        assert retrieved_bid.id == created_bid.id
        assert retrieved_bid.bid_number == created_bid.bid_number

    async def test_get_bid_by_id_not_found(self, bid_repo):
        """Test getting non-existent bid raises exception."""
        with pytest.raises(NotFoundException, match="Bid not found"):
            await bid_repo.get_by_id(uuid4(), uuid4())

    async def test_update_bid(self, bid_repo, sample_bid_data):
        """Test updating bid."""
        bid = await bid_repo.create(sample_bid_data)

        update_data = BidUpdate(
            title="Updated Title",
            bid_amount=150000.00
        )

        updated_bid = await bid_repo.update(bid.id, sample_bid_data.company_id, update_data)

        assert updated_bid.title == "Updated Title"
        assert float(updated_bid.bid_amount) == 150000.00

    async def test_update_bid_final_status(self, bid_repo, sample_bid_data):
        """Test updating bid in final status fails."""
        bid = await bid_repo.create(sample_bid_data)

        # Transition to final status
        await bid_repo.transition_status(
            bid.id, sample_bid_data.company_id, BidStatus.WON
        )

        update_data = BidUpdate(title="Should not work")

        with pytest.raises(ValidationException, match="cannot be edited"):
            await bid_repo.update(bid.id, sample_bid_data.company_id, update_data)

    async def test_transition_status_valid(self, bid_repo, sample_bid_data):
        """Test valid status transition."""
        bid = await bid_repo.create(sample_bid_data)

        # Transition from DRAFT to REVIEWING
        updated_bid, outcome = await bid_repo.transition_status(
            bid.id, sample_bid_data.company_id, BidStatus.REVIEWING
        )

        assert updated_bid.status == BidStatus.REVIEWING
        assert updated_bid.previous_status == BidStatus.DRAFT
        assert outcome is None

    async def test_transition_status_invalid(self, bid_repo, sample_bid_data):
        """Test invalid status transition fails."""
        bid = await bid_repo.create(sample_bid_data)

        # Try to transition directly to WON (invalid)
        with pytest.raises(ValidationException, match="Cannot transition"):
            await bid_repo.transition_status(
                bid.id, sample_bid_data.company_id, BidStatus.WON
            )

    async def test_transition_status_requires_outcome(self, bid_repo, sample_bid_data):
        """Test final status transition requires outcome record."""
        bid = await bid_repo.create(sample_bid_data)

        # Transition to SUBMITTED first
        await bid_repo.transition_status(
            bid.id, sample_bid_data.company_id, BidStatus.SUBMITTED
        )

        # Try to transition to LOST without outcome
        with pytest.raises(ValidationException, match="Outcome record is required"):
            await bid_repo.transition_status(
                bid.id, sample_bid_data.company_id, BidStatus.LOST
            )

    async def test_transition_status_with_outcome(self, bid_repo, sample_bid_data):
        """Test final status transition with outcome record."""
        bid = await bid_repo.create(sample_bid_data)

        # Transition to SUBMITTED first
        await bid_repo.transition_status(
            bid.id, sample_bid_data.company_id, BidStatus.SUBMITTED
        )

        # Create outcome data
        outcome_data = BidOutcomeRecordCreate(
            bid_id=bid.id,
            outcome=BidOutcome.LOST,
            loss_reason=LossReason.PRICE_TOO_HIGH,
            loss_reason_details="Our bid was too expensive",
            winning_bidder="Competitor Ltd",
            winning_amount=95000.00
        )

        # Transition to LOST with outcome
        updated_bid, outcome = await bid_repo.transition_status(
            bid.id, sample_bid_data.company_id, BidStatus.LOST, outcome_data
        )

        assert updated_bid.status == BidStatus.LOST
        assert updated_bid.is_final_status is True
        assert outcome is not None
        assert outcome.outcome == BidOutcome.LOST
        assert outcome.loss_reason == LossReason.PRICE_TOO_HIGH

    async def test_get_bids_with_filters(self, bid_repo, sample_bid_data):
        """Test getting bids with filters."""
        company_id = sample_bid_data.company_id

        # Create multiple bids
        bid1 = await bid_repo.create(sample_bid_data)

        bid2_data = BidCreate(
            company_id=company_id,
            tender_id=uuid4(),
            bid_number="BID-2024-002",
            title="Another Bid",
            bid_amount=200000.00,
            submission_deadline=datetime.utcnow() + timedelta(days=45)
        )
        bid2 = await bid_repo.create(bid2_data)

        # Test status filter
        filters = BidSearchFilters(status=BidStatus.DRAFT)
        bids, total = await bid_repo.get_by_company(company_id, filters)

        assert len(bids) == 2
        assert total == 2

        # Update one bid status
        await bid_repo.transition_status(
            bid1.id, company_id, BidStatus.REVIEWING
        )

        filters = BidSearchFilters(status=BidStatus.DRAFT)
        bids, total = await bid_repo.get_by_company(company_id, filters)

        assert len(bids) == 1
        assert total == 1
        assert bids[0].bid_number == "BID-2024-002"

    async def test_get_stats(self, bid_repo, sample_bid_data):
        """Test getting bid statistics."""
        company_id = sample_bid_data.company_id

        # Create bids with different statuses
        bid1 = await bid_repo.create(sample_bid_data)
        bid2_data = BidCreate(
            company_id=company_id,
            tender_id=uuid4(),
            bid_number="BID-2024-002",
            title="Another Bid",
            bid_amount=200000.00,
            submission_deadline=datetime.utcnow() + timedelta(days=45)
        )
        bid2 = await bid_repo.create(bid2_data)

        # Transition one bid to submitted
        await bid_repo.transition_status(
            bid1.id, company_id, BidStatus.SUBMITTED
        )

        stats = await bid_repo.get_stats(company_id)

        assert stats["total_bids"] == 2
        assert stats["draft_bids"] == 1
        assert stats["submitted_bids"] == 1
        assert stats["total_bid_value"] == 300000.00
        assert stats["win_rate"] == 0.0  # No wins yet


class TestBidLifecycleService(TestDatabase):
    """Test BidLifecycleService operations."""

    @pytest.fixture
    def bid_service(self, session):
        from app.infrastructure.groq_client import GroqClient

        return BidLifecycleService(
            bid_repo=BidRepository(session),
            outcome_repo=BidOutcomeRecordRepository(session),
            payment_repo=BidPaymentRepository(session),
            follow_up_repo=BidFollowUpRepository(session),
            groq_client=GroqClient()
        )

    async def test_create_bid_service(self, bid_service):
        """Test creating bid through service."""
        bid_data = BidCreate(
            company_id=uuid4(),
            tender_id=uuid4(),
            bid_number="BID-2024-001",
            title="Test Bid",
            bid_amount=100000.00,
            submission_deadline=datetime.utcnow() + timedelta(days=30)
        )

        bid_response = await bid_service.create_bid(bid_data)

        assert bid_response.id is not None
        assert bid_response.bid_number == "BID-2024-001"
        assert bid_response.status == BidStatus.DRAFT
        assert bid_response.can_edit is True

    async def test_transition_bid_status_service(self, bid_service):
        """Test status transition through service."""
        bid_data = BidCreate(
            company_id=uuid4(),
            tender_id=uuid4(),
            bid_number="BID-2024-001",
            title="Test Bid",
            bid_amount=100000.00,
            submission_deadline=datetime.utcnow() + timedelta(days=30)
        )

        bid = await bid_service.create_bid(bid_data)

        # Transition to SUBMITTED
        status_transition = BidStatusTransition(
            new_status=BidStatus.SUBMITTED,
            reason="Ready to submit"
        )

        bid_response, outcome_response = await bid_service.transition_bid_status(
            bid.id, bid_data.company_id, status_transition
        )

        assert bid_response.status == BidStatus.SUBMITTED
        assert bid_response.submission_date is not None
        assert outcome_response is None

    async def test_transition_to_lost_with_outcome(self, bid_service):
        """Test transition to LOST with outcome record."""
        bid_data = BidCreate(
            company_id=uuid4(),
            tender_id=uuid4(),
            bid_number="BID-2024-001",
            title="Test Bid",
            bid_amount=100000.00,
            submission_deadline=datetime.utcnow() + timedelta(days=30)
        )

        bid = await bid_service.create_bid(bid_data)

        # First transition to SUBMITTED
        status_transition1 = BidStatusTransition(new_status=BidStatus.SUBMITTED)
        await bid_service.transition_bid_status(
            bid.id, bid_data.company_id, status_transition1
        )

        # Transition to LOST with outcome
        status_transition2 = BidStatusTransition(
            new_status=BidStatus.LOST,
            reason="Lost bid"
        )

        outcome_data = BidOutcomeRecordCreate(
            bid_id=bid.id,
            outcome=BidOutcome.LOST,
            loss_reason=LossReason.PRICE_TOO_HIGH,
            loss_reason_details="Too expensive",
            winning_bidder="Competitor Ltd",
            winning_amount=95000.00
        )

        bid_response, outcome_response = await bid_service.transition_bid_status(
            bid.id, bid_data.company_id, status_transition2, outcome_data
        )

        assert bid_response.status == BidStatus.LOST
        assert outcome_response is not None
        assert outcome_response.outcome == BidOutcome.LOST
        assert outcome_response.loss_reason == LossReason.PRICE_TOO_HIGH

    async def test_get_bid_stats_service(self, bid_service):
        """Test getting bid statistics through service."""
        company_id = uuid4()

        # Create multiple bids
        bid1_data = BidCreate(
            company_id=company_id,
            tender_id=uuid4(),
            bid_number="BID-2024-001",
            title="Test Bid 1",
            bid_amount=100000.00,
            submission_deadline=datetime.utcnow() + timedelta(days=30)
        )

        bid2_data = BidCreate(
            company_id=company_id,
            tender_id=uuid4(),
            bid_number="BID-2024-002",
            title="Test Bid 2",
            bid_amount=200000.00,
            submission_deadline=datetime.utcnow() + timedelta(days=45)
        )

        await bid_service.create_bid(bid1_data)
        await bid_service.create_bid(bid2_data)

        stats = await bid_service.get_bid_stats(company_id)

        assert stats.total_bids == 2
        assert stats.draft_bids == 2
        assert stats.total_bid_value == 300000.00
        assert stats.win_rate == 0.0
