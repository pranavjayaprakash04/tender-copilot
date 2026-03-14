"""Tests for tender matching service."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.contexts.company_profile.repository import CompanyProfileRepository
from app.contexts.tender_discovery.repository import TenderRepository
from app.contexts.tender_matching.repository import (
    CompanyEmbeddingRepository,
    TenderEmbeddingRepository,
    TenderMatchRepository,
)
from app.contexts.tender_matching.service import TenderMatchingService
from app.shared.exceptions import NotFoundException, ValidationException


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
    repo = AsyncMock(spec=CompanyProfileRepository)
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
            mock_company_embedding.capabilities_embedding,
            limit=50,
            min_score=0.3,
            trace_id=None
        )

    @pytest.mark.asyncio
    async def test_find_matches_for_company_validates_embedding(
        self,
        matching_service,
        mock_match_repo,
        mock_company_embedding_repo,
        sample_company_id
    ):
        """Test that find_matches_for_company validates company embedding exists."""
        # Setup - no embedding found
        mock_company_embedding_repo.get_by_company_id.return_value = None

        # Execute & Assert
        with pytest.raises(ValidationException, match="Company must have embedding to find matches"):
            await matching_service.find_matches_for_company(
                company_id=sample_company_id,
                limit=50,
                min_score=0.3
            )

        # Verify repository was called
        mock_company_embedding_repo.get_by_company_id.assert_called_once_with(sample_company_id)

    @pytest.mark.asyncio
    async def test_find_matches_for_tender_validates_embedding(
        self,
        matching_service,
        mock_tender_embedding_repo,
        sample_tender_id
    ):
        """Test that find_matches_for_tender validates tender embedding exists."""
        # Setup - no embedding found
        mock_tender_embedding_repo.get_by_tender_id.return_value = None

        # Execute & Assert
        with pytest.raises(ValidationException, match="Tender must have embedding to find matches"):
            await matching_service.find_matches_for_tender(
                tender_id=sample_tender_id,
                limit=50,
                min_score=0.3
            )

        # Verify repository was called
        mock_tender_embedding_repo.get_by_tender_id.assert_called_once_with(sample_tender_id)

    @pytest.mark.asyncio
    async def test_find_matches_for_company_success(
        self,
        matching_service,
        mock_match_repo,
        mock_company_embedding_repo,
        sample_company_id,
        mock_company_embedding
    ):
        """Test successful find_matches_for_company call."""
        # Setup
        mock_company_embedding_repo.get_by_company_id.return_value = mock_company_embedding
        
        mock_match = Mock()
        mock_match.match_score = 0.85
        mock_match.tender_id = uuid4()
        mock_match_repo.find_similar_tenders.return_value = [mock_match]

        # Execute
        result = await matching_service.find_matches_for_company(
            company_id=sample_company_id,
            limit=10,
            min_score=0.5
        )

        # Assert
        assert len(result) == 1
        assert result[0] == mock_match
        mock_company_embedding_repo.get_by_company_id.assert_called_once_with(sample_company_id)
        mock_match_repo.find_similar_tenders.assert_called_once_with(
            mock_company_embedding.capabilities_embedding,
            limit=10,
            min_score=0.5,
            trace_id=None
        )
