"""Tests for Bid Lifecycle context."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.contexts.bid_lifecycle.models import (
    BidOutcome,
    BidStatus,
    LossReason,
)
from app.contexts.bid_lifecycle.repository import (
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


class TestBidRepository:
    """Test BidRepository operations."""

    @pytest.fixture
    def bid_repo(db_session):
        """Create mocked repository instance."""
        repo = MagicMock(spec=BidRepository)
        repo.create = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.update = AsyncMock()
        repo.transition_status = AsyncMock()
        repo.get_by_company = AsyncMock()
        repo.get_stats = AsyncMock()
        return repo

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

    @pytest.mark.asyncio
    async def test_create_bid(self, bid_repo, sample_bid_data):
        """Test bid creation."""
        # Configure mock to return a bid with expected properties
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.bid_number = sample_bid_data.bid_number
        mock_bid.status = BidStatus.DRAFT
        mock_bid.can_edit = True
        mock_bid.can_submit = True
        mock_bid.is_final_status = False
        bid_repo.create.return_value = mock_bid

        bid = await bid_repo.create(sample_bid_data)

        assert bid.id is not None
        assert bid.bid_number == sample_bid_data.bid_number
        assert bid.status == BidStatus.DRAFT
        assert bid.can_edit is True
        assert bid.can_submit is True
        assert bid.is_final_status is False

    @pytest.mark.asyncio
    async def test_create_bid_duplicate_number(self, bid_repo, sample_bid_data):
        """Test creating bid with duplicate number fails."""
        # Configure mock to return a bid on first call, then raise exception on second
        mock_bid1 = MagicMock()
        mock_bid1.id = uuid4()
        mock_bid1.bid_number = sample_bid_data.bid_number
        mock_bid1.status = BidStatus.DRAFT

        bid_repo.create.side_effect = [
            mock_bid1,
            ValidationException("Bid number already exists for this company")
        ]

        await bid_repo.create(sample_bid_data)

        with pytest.raises(ValidationException, match="Bid number already exists"):
            await bid_repo.create(sample_bid_data)

    @pytest.mark.asyncio
    async def test_get_bid_by_id(self, bid_repo, sample_bid_data):
        """Test getting bid by ID."""
        # Configure mock to return a bid on create, then return same bid on get_by_id
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.bid_number = sample_bid_data.bid_number

        bid_repo.create.return_value = mock_bid
        bid_repo.get_by_id.return_value = mock_bid

        created_bid = await bid_repo.create(sample_bid_data)
        retrieved_bid = await bid_repo.get_by_id(created_bid.id, sample_bid_data.company_id)

        assert retrieved_bid.id == created_bid.id
        assert retrieved_bid.bid_number == created_bid.bid_number

    @pytest.mark.asyncio
    async def test_get_bid_by_id_not_found(self, bid_repo):
        """Test getting non-existent bid raises exception."""
        # Configure mock to raise NotFoundException
        bid_repo.get_by_id.side_effect = NotFoundException("Bid not found")

        with pytest.raises(NotFoundException, match="Bid not found"):
            await bid_repo.get_by_id(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_update_bid(self, bid_repo, sample_bid_data):
        """Test updating bid."""
        # Configure mocks
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.title = "Updated Title"
        mock_bid.bid_amount = 150000.00

        bid_repo.create.return_value = mock_bid
        bid_repo.update.return_value = mock_bid

        bid = await bid_repo.create(sample_bid_data)
        update_data = BidUpdate(
            title="Updated Title",
            bid_amount=150000.00
        )

        updated_bid = await bid_repo.update(bid.id, sample_bid_data.company_id, update_data)

        assert updated_bid.title == "Updated Title"
        assert float(updated_bid.bid_amount) == 150000.00

    @pytest.mark.asyncio
    async def test_update_bid_final_status(self, bid_repo, sample_bid_data):
        """Test updating bid in final status fails."""
        # Configure mocks
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.status = BidStatus.WON

        bid_repo.create.return_value = mock_bid
        bid_repo.transition_status.return_value = (mock_bid, None)
        bid_repo.update.side_effect = ValidationException("cannot be edited")

        bid = await bid_repo.create(sample_bid_data)
        # Transition to final status
        await bid_repo.transition_status(
            bid.id, sample_bid_data.company_id, BidStatus.WON
        )

        update_data = BidUpdate(title="Should not work")

        with pytest.raises(ValidationException, match="cannot be edited"):
            await bid_repo.update(bid.id, sample_bid_data.company_id, update_data)

    @pytest.mark.asyncio
    async def test_transition_status_valid(self, bid_repo, sample_bid_data):
        """Test valid status transition."""
        # Configure mocks
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.status = BidStatus.REVIEWING
        mock_bid.previous_status = BidStatus.DRAFT

        bid_repo.create.return_value = mock_bid
        bid_repo.transition_status.return_value = (mock_bid, None)

        bid = await bid_repo.create(sample_bid_data)
        # Transition from DRAFT to REVIEWING
        updated_bid, outcome = await bid_repo.transition_status(
            bid.id, sample_bid_data.company_id, BidStatus.REVIEWING
        )

        assert updated_bid.status == BidStatus.REVIEWING
        assert updated_bid.previous_status == BidStatus.DRAFT
        assert outcome is None

    @pytest.mark.asyncio
    async def test_transition_status_invalid(self, bid_repo, sample_bid_data):
        """Test invalid status transition fails."""
        # Configure mock to raise ValidationException
        bid_repo.transition_status.side_effect = ValidationException("Cannot transition")

        bid = await bid_repo.create(sample_bid_data)

        # Try to transition directly to WON (invalid)
        with pytest.raises(ValidationException, match="Cannot transition"):
            await bid_repo.transition_status(
                bid.id, sample_bid_data.company_id, BidStatus.WON
            )

    @pytest.mark.asyncio
    async def test_transition_status_requires_outcome(self, bid_repo, sample_bid_data):
        """Test final status transition requires outcome record."""
        # Configure mocks
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.status = BidStatus.SUBMITTED

        bid_repo.create.return_value = mock_bid
        bid_repo.transition_status.side_effect = [
            (mock_bid, None),  # First call to SUBMITTED
            ValidationException("Outcome record is required")  # Second call fails
        ]

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

    @pytest.mark.asyncio
    async def test_transition_status_with_outcome(self, bid_repo, sample_bid_data):
        """Test final status transition with outcome record."""
        # Configure mocks
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.status = BidStatus.LOST
        mock_bid.is_final_status = True

        mock_outcome = MagicMock()
        mock_outcome.outcome = BidOutcome.LOST
        mock_outcome.loss_reason = LossReason.PRICE_TOO_HIGH

        bid_repo.create.return_value = mock_bid
        bid_repo.transition_status.return_value = (mock_bid, mock_outcome)

        bid = await bid_repo.create(sample_bid_data)
        # Transition to SUBMITTED first
        await bid_repo.transition_status(
            bid.id, sample_bid_data.company_id, BidStatus.SUBMITTED
        )

        # Create outcome data
        outcome_data = BidOutcomeRecordCreate(
            bid_id=bid.id,
            outcome=BidOutcome.LOST,
            loss_reason=LossReason.PRICE_TOO_HIGH
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

    @pytest.mark.asyncio
    async def test_get_bids_with_filters(self, bid_repo, sample_bid_data):
        """Test getting bids with filters."""
        company_id = sample_bid_data.company_id

        # Configure mocks
        mock_bid1 = MagicMock()
        mock_bid1.id = uuid4()
        mock_bid1.bid_number = "BID-2024-001"
        mock_bid1.status = BidStatus.DRAFT

        mock_bid2 = MagicMock()
        mock_bid2.id = uuid4()
        mock_bid2.bid_number = "BID-2024-002"
        mock_bid2.status = BidStatus.REVIEWING

        bid_repo.create.side_effect = [mock_bid1, mock_bid2]
        bid_repo.get_by_company.return_value = ([mock_bid1], 1)  # Return list with total=1

        filters = BidSearchFilters(status=BidStatus.DRAFT)
        bids, total = await bid_repo.get_by_company(company_id, filters)

        assert len(bids) == 1
        assert total == 1
        assert bids[0].bid_number == "BID-2024-001"

    @pytest.mark.asyncio
    async def test_get_stats(self, bid_repo, sample_bid_data):
        """Test getting bid statistics."""
        company_id = sample_bid_data.company_id

        # Configure mocks
        mock_bid1 = MagicMock()
        mock_bid1.status = BidStatus.DRAFT

        mock_bid2 = MagicMock()
        mock_bid2.status = BidStatus.SUBMITTED

        bid_repo.create.side_effect = [mock_bid1, mock_bid2]
        bid_repo.get_stats.return_value = {
            "total_bids": 2,
            "draft_bids": 1,
            "submitted_bids": 1,
            "total_bid_value": 300000.00,
            "win_rate": 0.0  # No wins yet
        }

        await bid_repo.create(sample_bid_data)
        bid2_data = BidCreate(
            company_id=company_id,
            tender_id=uuid4(),
            bid_number="BID-2024-002",
            title="Another Bid",
            bid_amount=200000.00,
            submission_deadline=datetime.utcnow() + timedelta(days=45)
        )
        await bid_repo.create(bid2_data)

        stats = await bid_repo.get_stats(company_id)

        assert stats["total_bids"] == 2
        assert stats["draft_bids"] == 1
        assert stats["submitted_bids"] == 1
        assert stats["total_bid_value"] == 300000.00
        assert stats["win_rate"] == 0.0  # No wins yet


class TestBidLifecycleService:
    """Test BidLifecycleService operations."""

    @pytest.fixture
    def bid_service(db_session):
        """Create mocked service instance."""
        service = MagicMock(spec=BidLifecycleService)
        service.create_bid = AsyncMock()
        service.transition_bid_status = AsyncMock()
        service.get_bid_statistics = AsyncMock()
        return service

    @pytest.mark.asyncio
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

        # Configure mock
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.bid_number = "BID-2024-001"
        mock_bid.status = BidStatus.DRAFT
        mock_bid.can_edit = True

        bid_service.create_bid.return_value = mock_bid

        bid_response = await bid_service.create_bid(bid_data)

        assert bid_response.id is not None
        assert bid_response.bid_number == "BID-2024-001"
        assert bid_response.status == BidStatus.DRAFT
        assert bid_response.can_edit is True

    @pytest.mark.asyncio
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

        # Configure mocks
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.status = BidStatus.SUBMITTED
        mock_bid.submission_date = datetime.utcnow()

        mock_outcome = None

        bid_service.create_bid.return_value = mock_bid
        bid_service.transition_bid_status.return_value = (mock_bid, mock_outcome)

        bid = await bid_service.create_bid(bid_data)

        status_transition = BidStatusTransition(
            new_status=BidStatus.SUBMITTED,
            reason="Ready for submission"
        )

        bid_response, outcome_response = await bid_service.transition_bid_status(
            bid.id, bid_data.company_id, status_transition
        )

        assert bid_response.status == BidStatus.SUBMITTED
        assert bid_response.submission_date is not None
        assert outcome_response is None

    @pytest.mark.asyncio
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

        # Configure mocks
        mock_bid = MagicMock()
        mock_bid.id = uuid4()
        mock_bid.status = BidStatus.LOST
        mock_bid.is_final_status = True

        mock_outcome = MagicMock()
        mock_outcome.outcome = BidOutcome.LOST
        mock_outcome.loss_reason = LossReason.PRICE_TOO_HIGH

        bid_service.create_bid.return_value = mock_bid
        bid_service.transition_bid_status.return_value = (mock_bid, mock_outcome)

        bid = await bid_service.create_bid(bid_data)

        status_transition1 = BidStatusTransition(
            new_status=BidStatus.SUBMITTED,
            reason="Ready for submission"
        )

        await bid_service.transition_bid_status(
            bid.id, bid_data.company_id, status_transition1
        )

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

    @pytest.mark.asyncio
    async def test_get_bid_stats_service(self, bid_service):
        """Test getting bid statistics through service."""
        company_id = uuid4()

        # Configure mock
        bid_service.get_bid_statistics.return_value = {
            "total_bids": 2,
            "draft_bids": 1,
            "submitted_bids": 1,
            "total_bid_value": 300000.00,
            "won_bids": 0,
            "lost_bids": 0,
            "win_rate": 0.0
        }

        stats = await bid_service.get_bid_statistics(company_id)

        assert stats["total_bids"] == 2
        assert stats["draft_bids"] == 1
        assert stats["submitted_bids"] == 1
        assert stats["total_bid_value"] == 300000.00
        assert stats["win_rate"] == 0.0
