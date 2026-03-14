"""Test configuration and fixtures."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_async_session
from app.main import app

# Import all models to ensure they are registered with Base
from app.contexts.bid_lifecycle.models import Bid, BidFollowUp, BidOutcomeRecord, BidPayment
from app.contexts.company_profile.models import Company

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# Test session factory
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


class TestDatabase:
    """Test database helper."""
    
    @staticmethod
    async def create_tables():
        """Create all tables."""
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    @staticmethod
    async def drop_tables():
        """Drop all tables."""
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    @staticmethod
    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        """Get test session."""
        async with TestSessionLocal() as session:
            yield session


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Create tables
    await TestDatabase.create_tables()
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
    
    # Clean up
    await TestDatabase.drop_tables()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client."""
    # Override the dependency
    app.dependency_overrides[get_async_session] = lambda: db_session
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_company_id():
    """Sample company ID for testing."""
    return uuid4()


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid4()


@pytest.fixture
def sample_tender_id():
    """Sample tender ID for testing."""
    return uuid4()


@pytest.fixture
def sample_bid_id():
    """Sample bid ID for testing."""
    return uuid4()


@pytest.fixture
def sample_document_id():
    """Sample document ID for testing."""
    return uuid4()


@pytest.fixture
def mock_company_data():
    """Mock company data for testing."""
    return {
        "name": "Test Company",
        "description": "A test company for unit tests",
        "industry": "Technology",
        "size": "Small",
        "location": "Test City",
        "contact_email": "test@example.com",
        "contact_phone": "+1234567890",
        "website": "https://test.example.com",
        "capabilities_text": "Software development, web applications, mobile apps, cloud services, AI/ML solutions",
        "established_year": 2020,
        "employee_count": 50,
        "annual_revenue": 1000000,
        "certifications": ["ISO 9001", "CMMI Level 3"],
        "specializations": ["Web Development", "Mobile Development", "Cloud Computing"],
        "past_projects": [
            {
                "title": "Test Project 1",
                "description": "A test project",
                "client": "Test Client",
                "year": 2023,
                "value": 100000
            }
        ]
    }


@pytest.fixture
def mock_tender_data():
    """Mock tender data for testing."""
    return {
        "title": "Test Software Development Tender",
        "description": "A test tender for software development services",
        "organization_name": "Test Organization",
        "tender_value": 500000,
        "emd_amount": 25000,
        "bid_submission_deadline": "2024-12-31T23:59:59Z",
        "category": "Software Development",
        "sub_category": "Web Applications",
        "cpv_codes": ["72000000", "72200000"],
        "status": "open",
        "source": "test_portal",
        "tender_id": "TEST-2024-001",
        "publication_date": "2024-11-01T00:00:00Z"
    }


@pytest.fixture
def mock_bid_data():
    """Mock bid data for testing."""
    return {
        "bid_amount": 450000,
        "emd_amount": 25000,
        "bid_security_amount": 10000,
        "submission_deadline": "2024-12-31T23:59:59Z",
        "technical_proposal": "Test technical proposal content",
        "financial_proposal": "Test financial proposal content",
        "status": "draft"
    }


@pytest.fixture
def mock_compliance_document_data():
    """Mock compliance document data for testing."""
    return {
        "title": "Test Compliance Document",
        "document_type": "certificate",
        "description": "A test compliance document",
        "expiry_date": "2025-12-31T23:59:59Z",
        "issuing_authority": "Test Authority",
        "document_number": "TEST-DOC-001",
        "status": "valid"
    }


@pytest.fixture
def mock_user_data():
    """Mock user data for testing."""
    return {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "phone": "+1234567890",
        "role": "admin",
        "is_active": True
    }


@pytest.fixture(scope="session", autouse=True)
def mock_embedding_model():
    """Mock the embedding model to prevent HuggingFace network calls during tests."""
    with patch("app.contexts.tender_matching.embedding_service.get_embedding_model") as mock_model:
        mock_model.return_value = MagicMock()
        yield mock_model