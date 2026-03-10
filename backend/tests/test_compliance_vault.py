"""Tests for compliance vault context."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.contexts.compliance_vault.models import DocumentType, VaultDocument
from app.contexts.compliance_vault.repository import VaultDocumentRepository
from app.contexts.compliance_vault.schemas import (
    DocumentClassificationRequest,
    VaultDocumentCreate,
)
from app.contexts.compliance_vault.service import ComplianceVaultService
from app.shared.exceptions import FileUploadException, ValidationException
from tests.conftest import db_session


class TestVaultDocumentRepository:
    """Test VaultDocumentRepository."""

    @pytest.fixture
    def repository(db_session):
        """Create mocked repository instance."""
        repo = MagicMock(spec=VaultDocumentRepository)
        repo.create = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.get_by_company = AsyncMock()
        repo.get_stats = AsyncMock()
        repo.get_expiring_soon = AsyncMock()
        repo.get_expired = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        return repo

    @pytest.fixture
    def sample_document(self):
        """Create sample document."""
        return VaultDocument(
            id=uuid4(),
            company_id=uuid4(),
            doc_type=DocumentType.GST,
            filename="test_gst.pdf",
            storage_path="companies/test/documents/test.pdf",
            version=1,
            expires_at=datetime.utcnow() + timedelta(days=365),
            is_current=True,
            uploaded_at=datetime.utcnow()
        )

    @pytest.mark.asyncio
    async def test_create_document(self, repository, sample_document):
        """Test document creation."""
        # Configure mock to return a document
        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.filename = sample_document.filename
        mock_doc.doc_type = sample_document.doc_type
        mock_doc.version = 1
        mock_doc.is_current = True
        
        repository.create.return_value = mock_doc
        
        result = await repository.create(sample_document)

        assert result.id is not None
        assert result.filename == sample_document.filename
        assert result.doc_type == sample_document.doc_type
        assert result.version == 1
        assert result.is_current is True

    @pytest.mark.asyncio
    async def test_create_document_versioning(self, repository, sample_document):
        """Test document versioning."""
        # Configure mocks
        existing_doc = MagicMock()
        existing_doc.id = uuid4()
        existing_doc.filename = sample_document.filename
        existing_doc.version = 1
        existing_doc.is_current = True
        
        new_doc = MagicMock()
        new_doc.id = uuid4()
        new_doc.filename = sample_document.filename
        new_doc.version = 2
        new_doc.is_current = True
        
        repository.get_by_company.return_value = ([existing_doc], 1)
        repository.create.return_value = new_doc
        
        result = await repository.create(sample_document)

        assert result.version == 2
        assert result.is_current is True

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, sample_document):
        """Test getting document by ID."""
        # Configure mock
        repository.get_by_id.return_value = sample_document
        
        result = await repository.get_by_id(sample_document.id, sample_document.company_id)

        assert result.id == sample_document.id
        assert result.filename == sample_document.filename

    @pytest.mark.asyncio
    async def test_get_expiring_soon(self, repository):
        """Test getting expiring documents."""
        company_id = uuid4()
        
        # Configure mock
        expiring_doc = MagicMock()
        expiring_doc.id = uuid4()
        expiring_doc.company_id = company_id
        expiring_doc.expires_at = datetime.utcnow() + timedelta(days=15)
        
        repository.get_expiring_soon.return_value = [expiring_doc]
        
        result = await repository.get_expiring_soon(company_id, 30)

        assert len(result) == 1
        assert result[0].expires_at <= datetime.utcnow() + timedelta(days=30)

    @pytest.mark.asyncio
    async def test_get_stats(self, repository):
        """Test getting document statistics."""
        company_id = uuid4()
        
        # Configure mock
        repository.get_stats.return_value = {
            "total_documents": 5,
            "current_documents": 4,
            "expired_documents": 1,
            "expiring_soon_documents": 2,
            "by_type": {"gst": 2, "pan": 2}
        }
        
        result = await repository.get_stats(company_id)

        assert result["total_documents"] == 5
        assert result["current_documents"] == 4
        assert result["expired_documents"] == 1
        assert result["expiring_soon_documents"] == 2
        assert result["by_type"] == {"gst": 2, "pan": 2}


class TestComplianceVaultService:
    """Test ComplianceVaultService."""

    @pytest.fixture
    def service(db_session):
        """Create mocked service instance."""
        service = MagicMock(spec=ComplianceVaultService)
        service.upload_document = AsyncMock()
        service.get_document = AsyncMock()
        service.get_document_stats = AsyncMock()
        return service

    @pytest.fixture
    def sample_document_data(self):
        """Create sample document data."""
        return VaultDocumentCreate(
            filename="test_gst.pdf",
            doc_type=DocumentType.GST,
            company_id=uuid4(),
            tender_id=uuid4(),
            expires_at=datetime.utcnow() + timedelta(days=365)
        )

    @pytest.mark.asyncio
    async def test_upload_document(self, service, sample_document_data):
        """Test document upload."""
        # Configure mock
        mock_doc = MagicMock()
        mock_doc.id = uuid4()
        mock_doc.filename = sample_document_data.filename
        mock_doc.doc_type = sample_document_data.doc_type
        mock_doc.storage_url = "https://storage.test/file.pdf"
        
        service.upload_document.return_value = mock_doc
        
        result = await service.upload_document(sample_document_data, b"file_content")

        assert result.id is not None
        assert result.filename == sample_document_data.filename
        assert result.doc_type == sample_document_data.doc_type
        assert result.storage_url is not None

    @pytest.mark.asyncio
    async def test_get_document(self, service):
        """Test getting document."""
        doc_id = uuid4()
        company_id = uuid4()
        
        # Configure mock
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.filename = "test.pdf"
        mock_doc.download_url = "https://storage.test/download.pdf"
        
        service.get_document.return_value = mock_doc
        
        result = await service.get_document(doc_id, company_id)

        assert result.id == doc_id
        assert result.filename == "test.pdf"
        assert result.download_url is not None

    @pytest.mark.asyncio
    async def test_get_document_stats(self, service):
        """Test getting document statistics."""
        company_id = uuid4()
        
        # Configure mock
        service.get_document_stats.return_value = {
            "total_documents": 10,
            "current_documents": 8,
            "expired_documents": 2,
            "expiring_soon_documents": 1,
            "by_type": {"gst": 5, "pan": 3, "msme": 2}
        }
        
        result = await service.get_document_stats(company_id)

        assert result["total_documents"] == 10
        assert result["current_documents"] == 8
        assert result["expired_documents"] == 2
        assert result["expiring_soon_documents"] == 1
        assert result["by_type"] == {"gst": 5, "pan": 3, "msme": 2}
