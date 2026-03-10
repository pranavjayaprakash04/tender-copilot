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


class TestVaultDocumentRepository:
    """Test VaultDocumentRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.scalar_one_or_none = AsyncMock()
        session.scalars = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository instance."""
        return VaultDocumentRepository(mock_session)

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

    async def test_create_document(self, repository, mock_session, sample_document):
        """Test document creation."""
        doc_data = VaultDocumentCreate(
            company_id=sample_document.company_id,
            doc_type=sample_document.doc_type,
            filename=sample_document.filename,
            expires_at=sample_document.expires_at
        )

        mock_session.scalar_one_or_none.return_value = None
        mock_session.execute.return_value.scalar.return_value = sample_document.id
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_document

        result = await repository.create(doc_data)

        assert result.company_id == doc_data.company_id
        assert result.doc_type == doc_data.doc_type
        assert result.filename == doc_data.filename
        assert result.version == 1
        assert result.is_current is True
        mock_session.commit.assert_called_once()

    async def test_create_document_versioning(self, repository, mock_session, sample_document):
        """Test document versioning when duplicate exists."""
        doc_data = VaultDocumentCreate(
            company_id=sample_document.company_id,
            doc_type=sample_document.doc_type,
            filename=sample_document.filename,
            expires_at=sample_document.expires_at
        )

        # Mock existing document
        existing_doc = VaultDocument(
            id=uuid4(),
            company_id=sample_document.company_id,
            doc_type=sample_document.doc_type,
            filename=sample_document.filename,
            storage_path="old/path.pdf",
            version=1,
            expires_at=sample_document.expires_at,
            is_current=True,
            uploaded_at=datetime.utcnow()
        )

        mock_session.scalar_one_or_none.return_value = existing_doc
        mock_session.execute.return_value.scalar.return_value = sample_document.id
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_document

        result = await repository.create(doc_data)

        assert result.version == 2  # Should be incremented
        assert existing_doc.is_current is False  # Should be marked as not current
        mock_session.commit.assert_called()

    async def test_get_by_id(self, repository, mock_session, sample_document):
        """Test getting document by ID."""
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_document

        result = await repository.get_by_id(sample_document.id, sample_document.company_id)

        assert result.id == sample_document.id
        assert result.company_id == sample_document.company_id

    async def test_get_by_company(self, repository, mock_session):
        """Test getting documents by company."""
        company_id = uuid4()
        documents = [
            VaultDocument(
                id=uuid4(),
                company_id=company_id,
                doc_type=DocumentType.GST,
                filename="gst.pdf",
                storage_path="path1.pdf",
                version=1,
                is_current=True,
                uploaded_at=datetime.utcnow()
            ),
            VaultDocument(
                id=uuid4(),
                company_id=company_id,
                doc_type=DocumentType.PAN,
                filename="pan.pdf",
                storage_path="path2.pdf",
                version=1,
                is_current=True,
                uploaded_at=datetime.utcnow()
            )
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = documents
        mock_result.scalar.return_value = 2
        mock_session.execute.return_value = mock_result

        result, total = await repository.get_by_company(company_id)

        assert len(result) == 2
        assert total == 2

    async def test_get_expiring_soon(self, repository, mock_session):
        """Test getting expiring documents."""
        company_id = uuid4()
        expiring_doc = VaultDocument(
            id=uuid4(),
            company_id=company_id,
            doc_type=DocumentType.GST,
            filename="expiring.pdf",
            storage_path="path.pdf",
            version=1,
            expires_at=datetime.utcnow() + timedelta(days=15),
            is_current=True,
            uploaded_at=datetime.utcnow()
        )

        mock_session.execute.return_value.scalars.return_value.all.return_value = [expiring_doc]

        result = await repository.get_expiring_soon(company_id, 30)

        assert len(result) == 1
        assert result[0].expires_at <= datetime.utcnow() + timedelta(days=30)

    async def test_get_stats(self, repository, mock_session):
        """Test getting document statistics."""
        company_id = uuid4()

        # Mock stats queries
        mock_session.execute.side_effect = [
            MagicMock(scalar=lambda: 5),  # total
            MagicMock(scalar=lambda: 4),  # current
            MagicMock(scalar=lambda: 1),  # expired
            MagicMock(scalar=lambda: 2),  # expiring_soon
            MagicMock(all=lambda: [("gst", 2), ("pan", 2)])  # by_type
        ]

        result = await repository.get_stats(company_id)

        assert result["total_documents"] == 5
        assert result["current_documents"] == 4
        assert result["expired_documents"] == 1
        assert result["expiring_soon_documents"] == 2
        assert result["by_type"] == {"gst": 2, "pan": 2}


class TestComplianceVaultService:
    """Test ComplianceVaultService."""

    @pytest.fixture
    def mock_document_repo(self):
        """Create mock document repository."""
        repo = AsyncMock()
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
    def mock_mapping_repo(self):
        """Create mock mapping repository."""
        repo = AsyncMock()
        repo.create_mapping = AsyncMock()
        repo.get_by_tender = AsyncMock()
        return repo

    @pytest.fixture
    def mock_storage_client(self):
        """Create mock storage client."""
        client = AsyncMock()
        client.upload_file = AsyncMock()
        client.get_download_url = AsyncMock(return_value="https://test.url/file.pdf")
        client.delete_file = AsyncMock()
        return client

    @pytest.fixture
    def mock_groq_client(self):
        """Create mock Groq client."""
        client = AsyncMock()
        client.complete = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_document_repo, mock_mapping_repo, mock_storage_client, mock_groq_client):
        """Create service instance."""
        return ComplianceVaultService(
            document_repo=mock_document_repo,
            mapping_repo=mock_mapping_repo,
            storage_client=mock_storage_client,
            groq_client=mock_groq_client
        )

    @pytest.fixture
    def mock_file(self):
        """Create mock uploaded file."""
        file = MagicMock()
        file.filename = "test.pdf"
        file.content_type = "application/pdf"
        file.size = 1024 * 1024  # 1MB
        file.read = AsyncMock(return_value=b"pdf content")
        return file

    async def test_upload_document_success(self, service, mock_document_repo, mock_storage_client, mock_file):
        """Test successful document upload."""
        company_id = uuid4()
        doc_type = DocumentType.GST

        # Mock document creation
        document = VaultDocument(
            id=uuid4(),
            company_id=company_id,
            doc_type=doc_type,
            filename=mock_file.filename,
            storage_path="",
            version=1,
            is_current=True,
            uploaded_at=datetime.utcnow()
        )
        mock_document_repo.create.return_value = document

        result = await service.upload_document(
            file=mock_file,
            doc_type=doc_type,
            company_id=company_id,
            trace_id="test-trace"
        )

        assert result.filename == mock_file.filename
        assert result.doc_type == doc_type
        assert result.company_id == company_id
        mock_storage_client.upload_file.assert_called_once()
        mock_document_repo.update.assert_called_once()

    async def test_upload_document_invalid_file_type(self, service, mock_file):
        """Test upload with invalid file type."""
        mock_file.filename = "test.txt"

        with pytest.raises(ValidationException, match="Only PDF files are supported"):
            await service.upload_document(
                file=mock_file,
                doc_type=DocumentType.GST,
                company_id=uuid4(),
                trace_id="test-trace"
            )

    async def test_upload_document_file_too_large(self, service, mock_file):
        """Test upload with file too large."""
        mock_file.size = 11 * 1024 * 1024  # 11MB

        with pytest.raises(FileUploadException, match="File size exceeds 10MB limit"):
            await service.upload_document(
                file=mock_file,
                doc_type=DocumentType.GST,
                company_id=uuid4(),
                trace_id="test-trace"
            )

    async def test_classify_document(self, service, mock_groq_client):
        """Test document classification."""

        request = DocumentClassificationRequest(
            filename="gst_certificate.pdf",
            content_preview="GST Registration Certificate"
        )

        # Mock Groq response
        mock_result = MagicMock()
        mock_result.doc_type = DocumentType.GST
        mock_result.confidence = 0.95
        mock_result.suggested_expiry = datetime.utcnow() + timedelta(days=365)
        mock_result.reasoning = "Document contains GST registration details"

        mock_groq_client.complete.return_value = mock_result

        result = await service.classify_document(request, trace_id="test-trace")

        assert result.doc_type == DocumentType.GST
        assert result.confidence == 0.95
        assert result.reasoning == "Document contains GST registration details"
        mock_groq_client.complete.assert_called_once()

    async def test_get_document(self, service, mock_document_repo, mock_storage_client):
        """Test getting document with download URL."""
        company_id = uuid4()
        document = VaultDocument(
            id=uuid4(),
            company_id=company_id,
            doc_type=DocumentType.GST,
            filename="test.pdf",
            storage_path="path/test.pdf",
            version=1,
            is_current=True,
            uploaded_at=datetime.utcnow()
        )

        mock_document_repo.get_by_id.return_value = document
        mock_storage_client.get_download_url.return_value = "https://download.url/file.pdf"

        result = await service.get_document(document.id, company_id, trace_id="test-trace")

        assert result.id == document.id
        assert result.filename == document.filename
        assert result.download_url == "https://download.url/file.pdf"
        mock_storage_client.get_download_url.assert_called_once_with(document.storage_path)

    async def test_delete_document(self, service, mock_document_repo, mock_storage_client):
        """Test document deletion."""
        company_id = uuid4()
        document = VaultDocument(
            id=uuid4(),
            company_id=company_id,
            doc_type=DocumentType.GST,
            filename="test.pdf",
            storage_path="path/test.pdf",
            version=1,
            is_current=True,
            uploaded_at=datetime.utcnow()
        )

        mock_document_repo.get_by_id.return_value = document

        await service.delete_document(document.id, company_id, trace_id="test-trace")

        mock_storage_client.delete_file.assert_called_once_with(document.storage_path)
        mock_document_repo.delete.assert_called_once_with(document.id, company_id)

    async def test_get_document_stats(self, service, mock_document_repo):
        """Test getting document statistics."""
        company_id = uuid4()

        mock_document_repo.get_stats.return_value = {
            "total_documents": 10,
            "current_documents": 8,
            "expired_documents": 2,
            "expiring_soon_documents": 3,
            "by_type": {"gst": 3, "pan": 2, "iso": 3}
        }

        expiring_doc = VaultDocument(
            id=uuid4(),
            company_id=company_id,
            doc_type=DocumentType.GST,
            filename="expiring.pdf",
            storage_path="path.pdf",
            version=1,
            expires_at=datetime.utcnow() + timedelta(days=15),
            is_current=True,
            uploaded_at=datetime.utcnow()
        )
        mock_document_repo.get_expiring_soon.return_value = [expiring_doc]

        result = await service.get_document_stats(company_id, trace_id="test-trace")

        assert result.total_documents == 10
        assert result.current_documents == 8
        assert result.expired_documents == 2
        assert result.expiring_soon_documents == 3
        assert len(result.upcoming_expiries) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
