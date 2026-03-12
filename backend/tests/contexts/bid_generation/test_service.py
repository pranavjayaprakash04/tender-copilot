"""Tests for bid generation service."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.contexts.bid_generation.models import BidStatus, BidType
from app.contexts.bid_generation.repository import (
    BidGenerationAnalyticsRepository,
    BidGenerationRepository,
    BidTemplateRepository,
)
from app.contexts.bid_generation.service import BidGenerationService
from app.contexts.tender_discovery.repository import TenderRepository
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.shared.exceptions import LLMException, NotFoundException
from app.shared.lang_context import LangContext


@pytest.fixture
def mock_bid_repo():
    """Mock bid generation repository."""
    repo = AsyncMock(spec=BidGenerationRepository)
    return repo


@pytest.fixture
def mock_template_repo():
    """Mock template repository."""
    repo = AsyncMock(spec=BidTemplateRepository)
    return repo


@pytest.fixture
def mock_analytics_repo():
    """Mock analytics repository."""
    repo = AsyncMock(spec=BidGenerationAnalyticsRepository)
    return repo


@pytest.fixture
def mock_tender_repo():
    """Mock tender repository."""
    repo = AsyncMock(spec=TenderRepository)
    return repo


@pytest.fixture
def mock_groq_client():
    """Mock Groq client."""
    client = AsyncMock(spec=GroqClient)
    return client


@pytest.fixture
def bid_service(
    mock_bid_repo,
    mock_template_repo,
    mock_analytics_repo,
    mock_tender_repo,
    mock_groq_client
):
    """Bid generation service fixture."""
    return BidGenerationService(
        bid_repo=mock_bid_repo,
        template_repo=mock_template_repo,
        analytics_repo=mock_analytics_repo,
        tender_repo=mock_tender_repo,
        groq_client=mock_groq_client
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
def mock_tender():
    """Mock tender object."""
    tender = Mock()
    tender.id = uuid4()
    tender.title = "Test Software Development Tender"
    tender.description = "A test tender for software development"
    tender.organization_name = "Test Organization"
    tender.tender_value = 500000
    tender.emd_amount = 25000
    tender.bid_submission_deadline = "2024-12-31T23:59:59Z"
    tender.category = "Software Development"
    tender.sub_category = "Web Applications"
    tender.cpv_codes = ["72000000", "72200000"]
    return tender


@pytest.fixture
def mock_bid_generation():
    """Mock bid generation object."""
    bid_gen = Mock()
    bid_gen.id = uuid4()
    bid_gen.tender_id = uuid4()
    bid_gen.company_id = uuid4()
    bid_gen.bid_type = BidType.TECHNICAL
    bid_gen.language = "en"
    bid_gen.bid_title = "Test Bid"
    bid_gen.status = BidStatus.PENDING
    bid_gen.task_id = str(uuid4())
    bid_gen.template_used = None
    return bid_gen


class TestBidGenerationService:
    """Test bid generation service."""

    @pytest.mark.asyncio
    async def test_generate_bid_draft_success(
        self,
        bid_service,
        mock_bid_repo,
        mock_tender_repo,
        mock_groq_client,
        sample_company_id,
        sample_tender_id,
        mock_tender,
        mock_bid_generation
    ):
        """Test successful bid draft generation."""
        # Setup
        mock_tender_repo.get_by_id.return_value = mock_tender
        mock_bid_repo.get_by_task_id.return_value = mock_bid_generation

        # Mock the AI response
        mock_ai_response = Mock()
        mock_ai_response.model_dump.return_value = {
            "technical_proposal": "Test technical content",
            "executive_summary": "Test summary",
            "confidence_score": 0.85
        }
        mock_groq_client.complete.return_value = mock_ai_response

        # Mock the repository update
        mock_bid_repo.update_with_content.return_value = mock_bid_generation
        mock_bid_repo.update_status.return_value = None

        # Execute
        result = await bid_service.generate_bid_content(
            task_id=mock_bid_generation.task_id,
            company_id=sample_company_id
        )

        # Assert
        assert result == mock_bid_generation
        mock_tender_repo.get_by_id.assert_called_once_with(
            mock_bid_generation.tender_id, sample_company_id
        )
        mock_groq_client.complete.assert_called_once()

        # Verify Groq was called with correct model
        call_args = mock_groq_client.complete.call_args
        assert call_args[1]["model"] == GroqModel.PRIMARY

        # Verify LangContext was used and passed correctly
        assert "lang" in call_args[1]
        lang_context = call_args[1]["lang"]
        assert isinstance(lang_context, LangContext)
        assert lang_context.lang == "en"  # Default language
        assert "Respond in clear, simple English." == lang_context.output_instruction

    @pytest.mark.asyncio
    async def test_generate_bid_draft_company_not_found(
        self,
        bid_service,
        mock_bid_repo,
        mock_tender_repo,
        sample_company_id,
        sample_tender_id,
        mock_bid_generation
    ):
        """Test bid generation when company not found."""
        # Setup
        mock_tender_repo.get_by_id.return_value = None
        mock_bid_repo.get_by_task_id.return_value = mock_bid_generation

        # Execute & Assert
        with pytest.raises(NotFoundException, match="Tender not found"):
            await bid_service.generate_bid_content(
                task_id=mock_bid_generation.task_id,
                company_id=sample_company_id
            )

    @pytest.mark.asyncio
    async def test_generate_bid_draft_tender_not_found(
        self,
        bid_service,
        mock_bid_repo,
        sample_company_id,
        sample_tender_id
    ):
        """Test bid generation when tender not found."""
        # Setup - bid generation task not found
        mock_bid_repo.get_by_task_id.return_value = None

        # Execute & Assert
        with pytest.raises(NotFoundException, match="Bid generation task not found"):
            await bid_service.generate_bid_content(
                task_id="non-existent-task",
                company_id=sample_company_id
            )

    @pytest.mark.asyncio
    async def test_generate_bid_draft_llm_failure(
        self,
        bid_service,
        mock_bid_repo,
        mock_tender_repo,
        mock_groq_client,
        sample_company_id,
        sample_tender_id,
        mock_tender,
        mock_bid_generation
    ):
        """Test bid generation when LLM fails."""
        # Setup
        mock_tender_repo.get_by_id.return_value = mock_tender
        mock_bid_repo.get_by_task_id.return_value = mock_bid_generation
        mock_groq_client.complete.side_effect = LLMException("API Error")

        # Execute & Assert
        with pytest.raises(LLMException, match="API Error"):
            await bid_service.generate_bid_content(
                task_id=mock_bid_generation.task_id,
                company_id=sample_company_id
            )

    @pytest.mark.asyncio
    async def test_tamil_bid_uses_tamil_output_instruction(
        self,
        bid_service,
        mock_bid_repo,
        mock_tender_repo,
        mock_groq_client,
        sample_company_id,
        sample_tender_id,
        mock_tender,
        mock_bid_generation
    ):
        """Test that Tamil bids use Tamil output instruction."""
        # Setup - create Tamil bid generation
        tamil_bid_generation = Mock()
        tamil_bid_generation.id = uuid4()
        tamil_bid_generation.tender_id = sample_tender_id
        tamil_bid_generation.company_id = sample_company_id
        tamil_bid_generation.bid_type = BidType.TECHNICAL
        tamil_bid_generation.language = "ta"
        tamil_bid_generation.bid_title = "தமிழ் போட்டி"
        tamil_bid_generation.status = BidStatus.PENDING
        tamil_bid_generation.task_id = str(uuid4())
        tamil_bid_generation.template_used = None

        mock_tender_repo.get_by_id.return_value = mock_tender
        mock_bid_repo.get_by_task_id.return_value = tamil_bid_generation

        # Mock the AI response
        mock_ai_response = Mock()
        mock_ai_response.model_dump.return_value = {
            "technical_proposal": "தமிழ் தொழில்நுட்ப உள்ளடக்கம்",
            "executive_summary": "தமிழ் சுருக்கம்",
            "confidence_score": 0.85
        }
        mock_groq_client.complete.return_value = mock_ai_response
        mock_bid_repo.update_with_content.return_value = tamil_bid_generation
        mock_bid_repo.update_status.return_value = None

        # Execute
        await bid_service.generate_bid_content(
            task_id=tamil_bid_generation.task_id,
            company_id=sample_company_id
        )

        # Assert - Verify Tamil LangContext was used
        call_args = mock_groq_client.complete.call_args
        lang_context = call_args[1]["lang"]
        assert lang_context.lang == "ta"
        assert "தமிழ்" in lang_context.output_instruction
        assert "Respond ENTIRELY in Tamil" in lang_context.output_instruction
