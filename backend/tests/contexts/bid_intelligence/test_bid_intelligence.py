from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.contexts.bid_intelligence.consortium_schemas import (
    ConsortiumMatchRequest,
    ConsortiumMatchResponse,
)
from app.contexts.bid_intelligence.consortium_service import ConsortiumService
from app.contexts.bid_intelligence.schemas import (
    CompetitorAnalysisRequest,
    CompetitorAnalysisResponse,
    CompetitorInsight,
    WinProbabilityRequest,
    WinProbabilityResponse,
)
from app.contexts.bid_intelligence.service import BidIntelligenceService
from app.contexts.company_profile.models import Company
from app.contexts.tender_discovery.models import Tender
from app.contexts.bid_lifecycle.market_prices import MarketPrice


class TestBidIntelligence:
    """Test bid intelligence functionality."""

    @pytest.fixture
    def tender_id(self) -> UUID:
        """Test tender ID."""
        return UUID("12345678-1234-5678-1234-567812345678")

    @pytest.fixture
    def company_id(self) -> UUID:
        """Test company ID."""
        return UUID("87654321-4321-8765-4321-876543218765")

    @pytest.fixture
    def mock_groq_client(self) -> AsyncMock:
        """Mock Groq client."""
        return AsyncMock()

    @pytest.fixture
    def mock_tender_repo(self) -> AsyncMock:
        """Mock tender repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_company_profile_repo(self) -> AsyncMock:
        """Mock company profile repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_company_repo(self) -> AsyncMock:
        """Mock company profile repository."""
        return AsyncMock()

    @pytest.fixture
    def bid_intel_service(
        self, mock_groq_client: AsyncMock, mock_tender_repo: AsyncMock,
        mock_company_repo: AsyncMock, mock_session: AsyncMock
    ) -> BidIntelligenceService:
        """Bid intelligence service with mocked dependencies."""
        return BidIntelligenceService(
            mock_groq_client, mock_tender_repo, mock_company_repo, mock_session
        )

    async def test_win_probability_high_when_price_matches_market(
        self, bid_intel_service: BidIntelligenceService, tender_id: UUID, company_id: UUID,
        mock_tender_repo: AsyncMock, mock_company_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test win probability is high when bid price matches market average."""
        # Setup
        tender = MagicMock(spec=Tender)
        tender.category = "construction"
        mock_tender_repo.get_by_id.return_value = tender

        market_price = MagicMock(spec=MarketPrice)
        market_price.avg_estimated_value = 1000000.0
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = market_price
        mock_session.execute.return_value = mock_result

        company_profile = MagicMock(spec=Company)
        company_profile.capabilities = ["construction", "engineering"]
        mock_company_repo.get_by_id.return_value = company_profile

        req = WinProbabilityRequest(tender_id=tender_id, company_id=company_id, our_bid_amount=1000000.0)

        # Execute
        result = await bid_intel_service.calculate_win_probability(req)

        # Verify
        assert isinstance(result, WinProbabilityResponse)
        assert result.tender_id == tender_id
        assert result.win_probability > 0.7  # High probability
        assert result.confidence == "high"
        assert result.market_avg == 1000000.0
        assert "Market price alignment" in " ".join(result.factors)

    async def test_win_probability_low_when_price_far_from_market(
        self, bid_intel_service: BidIntelligenceService, tender_id: UUID, company_id: UUID,
        mock_tender_repo: AsyncMock, mock_company_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test win probability is low when bid price is far from market average."""
        # Setup
        tender = MagicMock(spec=Tender)
        tender.category = "construction"
        mock_tender_repo.get_by_id.return_value = tender

        market_price = MagicMock(spec=MarketPrice)
        market_price.avg_estimated_value = 1000000.0
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = market_price
        mock_session.execute.return_value = mock_result

        company_profile = MagicMock(spec=Company)
        company_profile.capabilities = ["construction", "engineering"]
        mock_company_repo.get_by_id.return_value = company_profile

        req = WinProbabilityRequest(tender_id=tender_id, company_id=company_id, our_bid_amount=2000000.0)

        # Execute
        result = await bid_intel_service.calculate_win_probability(req)

        # Verify
        assert isinstance(result, WinProbabilityResponse)
        assert result.tender_id == tender_id
        assert result.win_probability < 0.5  # Low probability
        assert result.confidence in ["low", "medium"]
        assert result.market_avg == 1000000.0

    async def test_win_probability_uses_past_win_rate(
        self, bid_intel_service: BidIntelligenceService, tender_id: UUID, company_id: UUID,
        mock_tender_repo: AsyncMock, mock_company_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test win probability calculation uses past win rate."""
        # Setup
        tender = MagicMock(spec=Tender)
        tender.category = "construction"
        mock_tender_repo.get_by_id.return_value = tender

        market_price = MagicMock(spec=MarketPrice)
        market_price.avg_estimated_value = 1000000.0
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = market_price
        mock_session.execute.return_value = mock_result

        company_profile = MagicMock(spec=Company)
        company_profile.capabilities = ["construction", "engineering"]
        mock_company_repo.get_by_id.return_value = company_profile

        req = WinProbabilityRequest(tender_id=tender_id, company_id=company_id, our_bid_amount=1000000.0)

        # Execute
        result = await bid_intel_service.calculate_win_probability(req)

        # Verify
        assert isinstance(result, WinProbabilityResponse)
        assert "Past win rate" in " ".join(result.factors)
        # The mock service uses 0.6 as past win rate (40% weight in calculation)

    async def test_competitor_analysis_returns_structured_response(
        self, bid_intel_service: BidIntelligenceService, tender_id: UUID, company_id: UUID,
        mock_groq_client: AsyncMock, mock_tender_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test competitor analysis returns structured response."""
        # Setup
        tender = MagicMock(spec=Tender)
        tender.title = "Test Construction Project"
        tender.category = "construction"
        tender.estimated_value = 1500000.0
        tender.portal = "CPPP"
        tender.submission_deadline = datetime.now(timezone.utc)
        mock_tender_repo.get_by_id.return_value = tender

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mock_response = MagicMock()
        mock_response.content = "Mock AI response"
        mock_groq_client.complete.return_value = mock_response

        req = CompetitorAnalysisRequest(tender_id=tender_id, company_id=company_id, lang="en")

        # Execute
        result = await bid_intel_service.analyze_competitors(req)

        # Verify
        assert isinstance(result, CompetitorAnalysisResponse)
        assert result.tender_id == tender_id
        assert result.company_id == company_id
        assert result.analysis_lang == "en"
        assert len(result.insights) > 0
        assert all(isinstance(insight, CompetitorInsight) for insight in result.insights)

    async def test_market_price_returns_avg_min_max(
        self, bid_intel_service: BidIntelligenceService, mock_session: AsyncMock
    ) -> None:
        """Test market price endpoint returns avg, min, max values."""
        # Setup
        market_price = MagicMock(spec=MarketPrice)
        market_price.tender_category = "construction"
        market_price.avg_estimated_value = 1000000.0
        market_price.min_value = 500000.0
        market_price.max_value = 2000000.0
        market_price.sample_count = 50
        market_price.last_refreshed = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = market_price
        mock_session.execute.return_value = mock_result

        # Execute
        result = await bid_intel_service.get_market_price("construction")

        # Verify
        assert result is not None
        assert result["category"] == "construction"
        assert result["avg_price"] == 1000000.0
        assert result["min_price"] == 500000.0
        assert result["max_price"] == 2000000.0
        assert result["sample_count"] == 50

    async def test_consortium_matching_excludes_requesting_company(
        self, mock_company_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test consortium matching excludes the requesting company."""
        # Setup
        tender_id = UUID("12345678-1234-5678-1234-567812345678")
        company_id = UUID("87654321-4321-8765-4321-876543218765")
        other_company_id = UUID("11111111-1111-1111-1111-111111111111")

        requesting_company = MagicMock(spec=Company)
        requesting_company.id = company_id
        requesting_company.name = "Requesting Company"
        requesting_company.capabilities = ["construction"]
        requesting_company.location = "Chennai"

        other_company = MagicMock(spec=Company)
        other_company.id = other_company_id
        other_company.name = "Other Company"
        other_company.capabilities = ["construction", "engineering"]
        other_company.location = "Mumbai"

        mock_company_repo.get_all_companies.return_value = [requesting_company, other_company]

        consortium_service = ConsortiumService(mock_company_repo, None, mock_session)

        req = ConsortiumMatchRequest(
            tender_id=tender_id,
            company_id=company_id,
            required_capabilities=["construction"]
        )

        # Execute
        result = await consortium_service.find_consortium_partners(req)

        # Verify
        assert isinstance(result, ConsortiumMatchResponse)
        assert result.tender_id == tender_id
        assert len(result.recommended_partners) == 1
        assert result.recommended_partners[0].company_id == other_company_id
        assert result.recommended_partners[0].company_name == "Other Company"

    async def test_consortium_matching_scores_by_capability_overlap(
        self, mock_company_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test consortium matching scores by capability overlap percentage."""
        # Setup
        tender_id = UUID("12345678-1234-5678-1234-567812345678")
        company_id = UUID("87654321-4321-8765-4321-876543218765")

        partial_match_company = MagicMock(spec=Company)
        partial_match_company.id = UUID("11111111-1111-1111-1111-111111111111")
        partial_match_company.name = "Partial Match"
        partial_match_company.capabilities = ["construction"]
        partial_match_company.location = "Delhi"

        full_match_company = MagicMock(spec=Company)
        full_match_company.id = UUID("22222222-2222-2222-2222-222222222222")
        full_match_company.name = "Full Match"
        full_match_company.capabilities = ["construction", "engineering", "project_management"]
        full_match_company.location = "Bangalore"

        mock_company_repo.get_all_companies.return_value = [partial_match_company, full_match_company]

        consortium_service = ConsortiumService(mock_company_repo, None, mock_session)

        req = ConsortiumMatchRequest(
            tender_id=tender_id,
            company_id=company_id,
            required_capabilities=["construction", "engineering", "project_management"]
        )

        # Execute
        result = await consortium_service.find_consortium_partners(req)

        # Verify
        assert isinstance(result, ConsortiumMatchResponse)
        assert len(result.recommended_partners) == 2
        
        # Full match should have higher score and come first
        full_match = next(p for p in result.recommended_partners if p.company_name == "Full Match")
        partial_match = next(p for p in result.recommended_partners if p.company_name == "Partial Match")
        
        assert full_match.match_score > partial_match.match_score
        assert full_match.match_score == 1.0  # 100% match
        assert partial_match.match_score == 1/3  # 33% match (1 of 3 capabilities)
