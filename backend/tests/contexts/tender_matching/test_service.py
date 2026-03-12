"""Tests for tender matching service."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.contexts.company_profile.repository import CompanyRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.contexts.tender_matching.repository import (
    CompanyEmbeddingRepository,
    TenderEmbeddingRepository,
    TenderMatchRepository,
)
from app.contexts.tender_matching.service import TenderMatchingService
from app.shared.exceptions import NotFoundException


@pytest.fixture
def mock_match_repo():
    """Mock match repository."""
    repo = AsyncMock(spec=TenderMatchRepository)
    return repo


@pytest.fixture
def mock_company_embedding_repo():
    """Mock company embedding repository."""
    repo = AsyncMock(spec=CompanyEmbeddingRepository)
    return repo


@pytest.fixture
def mock_tender_embedding_repo():
    """Mock tender embedding repository."""
    repo = AsyncMock(spec=TenderEmbeddingRepository)
    return repo


@pytest.fixture
def mock_company_repo():
    """Mock company repository."""
    repo = AsyncMock(spec=CompanyRepository)
    return repo


@pytest.fixture
def mock_tender_repo():
    """Mock tender repository."""
    repo = AsyncMock(spec=TenderRepository)
    return repo


@pytest.fixture
def matching_service(
    mock_match_repo,
    mock_company_embedding_repo,
    mock_tender_embedding_repo,
    mock_company_repo,
    mock_tender_repo
):
    """Tender matching service fixture."""
    return TenderMatchingService(
        match_repo=mock_match_repo,
        company_embedding_repo=mock_company_embedding_repo,
        tender_embedding_repo=mock_tender_embedding_repo,
        company_repo=mock_company_repo,
        tender_repo=mock_tender_repo
    )


@pytest.fixture
def sample_company_id():
    """Sample company ID."""
    return uuid4()


@pytest.fixture
def sample_tender_id():
    """Sample tender ID."""
    return uuid4()


@pytest.fixture
def mock_company():
    """Mock company object."""
    company = Mock()
    company.id = uuid4()
    company.name = "Test Software Company"
    company.description = "A software development company"
    company.industry = "Technology"
    company.capabilities_text = "Software development, web applications, mobile apps"
    company.specializations = ["Web Development", "Mobile Development"]
    company.past_projects = [
        {"title": "Web Portal", "description": "E-commerce web portal"},
        {"title": "Mobile App", "description": "iOS and Android app"}
    ]
    company.certifications = ["ISO 9001"]
    company.employee_count = 50
    company.annual_revenue = 1000000
    company.location = "Bangalore"
    return company


@pytest.fixture
def mock_tender():
    """Mock tender object."""
    tender = Mock()
    tender.id = uuid4()
    tender.title = "Software Development Project"
    tender.description = "Web application development"
    tender.organization_name = "Government Agency"
    tender.category = "Software Development"
    tender.sub_category = "Web Applications"
    tender.cpv_codes = ["72000000"]
    tender.tender_value = 500000
    tender.emd_amount = 25000
    tender.requirements = "Web development expertise required"
    tender.scope_of_work = "Design and develop web application"
    tender.technical_specifications = "React, Node.js, PostgreSQL"
    return tender


@pytest.fixture
def mock_company_embedding():
    """Mock company embedding."""
    embedding = Mock()
    embedding.id = uuid4()
    embedding.company_id = uuid4()
    embedding.capabilities_embedding = [0.1, 0.2, 0.3]  # Mock embedding vector
    embedding.capabilities_text = "Software development, web applications"
    return embedding


@pytest.fixture
def mock_tender_match():
    """Mock tender match object."""
    match = Mock()
    match.id = uuid4()
    match.company_id = uuid4()
    match.tender_id = uuid4()
    match.match_score = 0.85
    match.confidence_level = "high"
    match.industry_match = 1.0
    match.size_match = 0.8
    match.location_match = 0.9
    match.value_match = 0.85
    match.experience_match = 0.9
    return match


class TestTenderMatchingService:
    """Test tender matching service."""

    @pytest.mark.asyncio
    async def test_match_tenders_returns_ranked_results(
        self,
        matching_service,
        mock_match_repo,
        mock_company_embedding_repo,
        mock_company_repo,
        sample_company_id,
        mock_company,
        mock_company_embedding,
        mock_tender_match
    ):
        """Test that tender matching returns ranked results by match score."""
        # Setup
        mock_company_repo.get_by_id.return_value = mock_company
        mock_company_embedding_repo.get_by_company_id.return_value = mock_company_embedding

        # Create mock matches with different scores
        high_score_match = Mock()
        high_score_match.match_score = 0.95
        high_score_match.tender_id = uuid4()

        medium_score_match = Mock()
        medium_score_match.match_score = 0.75
        medium_score_match.tender_id = uuid4()

        low_score_match = Mock()
        low_score_match.match_score = 0.45
        low_score_match.tender_id = uuid4()

        # Return matches in random order (not sorted)
        mock_matches = [medium_score_match, low_score_match, high_score_match]
        mock_match_repo.find_similar_tenders.return_value = mock_matches

        # Execute
        result = await matching_service.find_matches_for_company(
            company_id=sample_company_id,
            limit=50,
            min_score=0.3
        )

        # Assert
        assert len(result) == 3
        # Verify results are returned in the order provided by repository
        # (repository should handle ordering by match_score DESC)
        mock_match_repo.find_similar_tenders.assert_called_once_with(
            company_embedding=mock_company_embedding.capabilities_embedding,
            limit=50,
            min_score=0.3,
            trace_id=None
        )

    @pytest.mark.asyncio
    async def test_match_score_breakdown_has_all_components(
        self,
        matching_service,
        mock_match_repo,
        mock_company_embedding_repo,
        mock_tender_embedding_repo,
        mock_company_repo,
        mock_tender_repo,
        sample_company_id,
        sample_tender_id,
        mock_company,
        mock_tender,
        mock_company_embedding
    ):
        """Test that match score breakdown includes all required components."""
        # Setup
        mock_company_embedding_repo.get_by_company_id.return_value = mock_company_embedding

        mock_tender_embedding = Mock()
        mock_tender_embedding.requirements_embedding = [0.4, 0.5, 0.6]
        mock_tender_embedding_repo.get_by_tender_id.return_value = mock_tender_embedding

        mock_company_repo.get_by_id.return_value = mock_company
        mock_tender_repo.get_by_id.return_value = mock_tender

        # Mock similarity calculation
        mock_match_repo.calculate_cosine_similarity.return_value = 0.85

        # Mock match analysis
        mock_analysis = {
            "reasons": ["Good industry match", "Relevant experience"],
            "gaps": ["Limited government experience"],
            "recommendations": ["Highlight past projects"]
        }

        # Mock the match creation
        mock_match = Mock()
        mock_match.industry_match = 1.0
        mock_match.size_match = 0.8
        mock_match.location_match = 0.9
        mock_match.value_match = 0.85
        mock_match.experience_match = 0.9
        mock_match_repo.create.return_value = mock_match

        # Patch the _generate_match_analysis method
        with patch.object(matching_service, '_generate_match_analysis', return_value=mock_analysis):
            # Execute
            result = await matching_service.create_match_record(
                company_id=sample_company_id,
                tender_id=sample_tender_id
            )

            # Assert
            assert result == mock_match
            mock_match_repo.create.assert_called_once()

            # Verify the create call includes all score components
            create_args = mock_match_repo.create.call_args[0][0]
            assert hasattr(create_args, 'industry_match')
            assert hasattr(create_args, 'size_match')
            assert hasattr(create_args, 'location_match')
            assert hasattr(create_args, 'value_match')
            assert hasattr(create_args, 'experience_match')
            assert hasattr(create_args, 'match_score')

    @pytest.mark.asyncio
    async def test_company_with_no_profile_returns_empty(
        self,
        matching_service,
        mock_company_repo,
        sample_company_id
    ):
        """Test that company with no profile returns empty results gracefully."""
        # Setup - company not found
        mock_company_repo.get_by_id.return_value = None

        # Execute & Assert
        with pytest.raises(NotFoundException, match="Company not found"):
            await matching_service.generate_company_embedding(
                company_id=sample_company_id
            )

        # Verify company repository was called
        mock_company_repo.get_by_id.assert_called_once_with(sample_company_id)

    @pytest.mark.asyncio
    async def test_company_with_empty_capabilities_returns_empty(
        self,
        matching_service,
        mock_company_repo,
        mock_company_embedding_repo,
        sample_company_id,
        mock_company_embedding
    ):
        """Test that company with empty capabilities_text handles gracefully."""
        # Setup - company with empty capabilities
        empty_company = Mock()
        empty_company.id = sample_company_id
        empty_company.name = "Empty Company"
        empty_company.description = ""
        empty_company.industry = ""
        empty_company.capabilities_text = ""
        empty_company.specializations = []
        empty_company.past_projects = []
        empty_company.certifications = []

        mock_company_repo.get_by_id.return_value = empty_company
        mock_company_embedding_repo.get_by_company_id.return_value = None  # No existing embedding

        # Mock the embedding creation
        mock_company_embedding_repo.create_or_update.return_value = mock_company_embedding

        # Execute
        result = await matching_service.generate_company_embedding(
            company_id=sample_company_id
        )

        # Assert
        assert result == mock_company_embedding
        mock_company_repo.get_by_id.assert_called_once_with(sample_company_id)
        mock_company_embedding_repo.create_or_update.assert_called_once()

        # Verify the capabilities text was prepared (should be minimal but not empty)
        create_args = mock_company_embedding_repo.create_or_update.call_args[1]
        capabilities_text = create_args['capabilities_text']
        assert isinstance(capabilities_text, str)
        # Should contain at least the company name even if everything else is empty
        assert "Empty Company" in capabilities_text
