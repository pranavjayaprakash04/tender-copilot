"""Integration tests for compliance vault API endpoints."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.contexts.compliance_vault.schemas import (
    VaultDocumentResponse,
    DocumentClassificationResponse,
    DocumentStatsResponse,
    DocumentListResponse
)
from app.contexts.compliance_vault.models import DocumentType


class TestComplianceVaultAPI:
    """Test compliance vault API endpoints."""

    @pytest.fixture
    def mock_document(self):
        """Create a mock vault document."""
        return VaultDocumentResponse(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            company_id=UUID("12345678-1234-5678-1234-567812345670"),
            filename="test.pdf",
            doc_type=DocumentType.GST,
            storage_path="companies/12345678-1234-5678-1234-567812345670/documents/12345678-1234-5678-1234-567812345678/test.pdf",
            version=1,
            is_current=True,
            uploaded_at=datetime.now(timezone.utc),
            expires_at=None,
            is_expired=False,
            days_until_expiry=None,
            is_expiring_soon=False
        )

    @pytest.fixture
    def test_app(self):
        """Create test app without middleware for testing."""
        app = create_app()
        # Remove middleware for testing
        app.user_middleware.clear()
        return app

    @pytest.fixture
    def client(self, test_app, mock_company_id, mock_document):
        """Create test client with dependency overrides."""
        from app.dependencies import get_current_company_id, get_current_user_id, get_db_session, get_lang_context, get_trace_id
        from app.contexts.compliance_vault.router import get_vault_service
        from uuid import UUID
        from app.shared.lang_context import LangContext
        
        TEST_USER_ID = "test-user-id"
        TEST_COMPANY_ID = UUID(mock_company_id)
        
        # Override dependencies
        def override_get_current_user_id():
            return TEST_USER_ID
            
        def override_get_current_company_id():
            return str(TEST_COMPANY_ID)
            
        def override_get_db_session():
            return AsyncMock()
            
        def override_get_vault_service():
            from app.shared.exceptions import ValidationException, FileUploadException
            
            mock_service = AsyncMock()
            
            # Create a side effect function for upload_document that validates file type
            async def mock_upload_document(file, doc_type, company_id, expires_at=None, lang=None, trace_id=None):
                # Validate file type like the real service
                if not file.filename.lower().endswith('.pdf'):
                    raise ValidationException("Only PDF files are supported")
                if not file.filename:
                    raise ValidationException("Filename is required")
                return mock_document
            
            # Configure mock methods to return real schema objects
            mock_service.upload_document.side_effect = mock_upload_document
            mock_service.list_documents.return_value = DocumentListResponse(
                documents=[mock_document],
                total=1,
                expiring_soon=[],
                expired=[]
            ), 1
            mock_service.classify_document.return_value = DocumentClassificationResponse(
                doc_type=DocumentType.GST,
                confidence=0.95,
                suggested_expiry=None,
                reasoning="Document contains GST registration"
            )
            mock_service.get_document_stats.return_value = DocumentStatsResponse(
                total_documents=1,
                current_documents=1,
                expired_documents=0,
                expiring_soon_documents=0,
                by_type={DocumentType.GST: 1},
                upcoming_expiries=[]
            )
            mock_service.get_required_documents_for_tender.return_value = [
                DocumentType.GST, DocumentType.PAN, DocumentType.EXPERIENCE_CERTIFICATE
            ]
            return mock_service
            
        def override_get_lang_context():
            return LangContext.from_lang("en")
            
        def override_get_trace_id():
            return "test-trace-id"
        
        test_app.dependency_overrides[get_current_user_id] = override_get_current_user_id
        test_app.dependency_overrides[get_current_company_id] = override_get_current_company_id
        test_app.dependency_overrides[get_db_session] = override_get_db_session
        test_app.dependency_overrides[get_vault_service] = override_get_vault_service
        test_app.dependency_overrides[get_lang_context] = override_get_lang_context
        test_app.dependency_overrides[get_trace_id] = override_get_trace_id
        
        return TestClient(test_app)

    @pytest.fixture
    def mock_company_id(self):
        """Mock company ID."""
        return str(uuid4())

    @pytest.fixture
    def auth_headers(self, mock_company_id):
        """Mock authentication headers."""
        return {
            "X-Company-ID": mock_company_id,
            "Authorization": "Bearer test-token"
        }

    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["version"] == "1.5.0"

    def test_upload_document_unauthorized(self, test_app):
        """Test upload without authentication (middleware bypassed)."""
        # Create a separate client without dependency overrides
        from fastapi.testclient import TestClient
        client = TestClient(test_app)
        
        # Without middleware, the dependency will fail when trying to get company_id
        response = client.post("/api/v1/vault/upload")
        # Should return 403 because get_current_company_id will raise AuthorizationException
        assert response.status_code == 403

    def test_upload_document_success(self, client, mock_company_id, mock_document):
        """Test successful document upload."""
        # Create test file
        files = {"file": ("test.pdf", b"pdf content", "application/pdf")}
        params = {"doc_type": "gst", "expires_at": "2024-12-31T23:59:59"}

        response = client.post(
            "/api/v1/vault/upload",
            files=files,
            params=params,
            headers={"Authorization": "Bearer test-token"}
        )

        # Should succeed with proper auth headers
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["filename"] == "test.pdf"
        assert data["data"]["doc_type"] == "gst"

    def test_list_documents(self, client):
        """Test listing documents."""
        response = client.get("/api/v1/vault/documents", headers={"Authorization": "Bearer test-token"})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_classify_document(self, client):
        """Test document classification."""
        payload = {
            "filename": "gst_certificate.pdf",
            "content_preview": "GST Registration Certificate"
        }

        response = client.post(
            "/api/v1/vault/classify",
            json=payload,
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["doc_type"] == "gst"
        assert data["data"]["confidence"] == 0.95

    def test_get_document_stats(self, client):
        """Test getting document statistics."""
        response = client.get("/api/v1/vault/stats", headers={"Authorization": "Bearer test-token"})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_documents"] == 1
        assert data["data"]["current_documents"] == 1

    def test_analyze_tender_requirements(self, client):
        """Test analyzing tender requirements."""
        params = {
            "tender_title": "Construction Project",
            "tender_requirements": "GST registration, experience certificate required"
        }

        response = client.post(
            "/api/v1/vault/tenders/analyze-requirements",
            params=params,
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert "gst" in data["data"]

    def test_upload_invalid_file_type(self, client):
        """Test upload with invalid file type."""
        files = {"file": ("test.txt", b"text content", "text/plain")}
        params = {"doc_type": "gst"}

        response = client.post(
            "/api/v1/vault/upload",
            files=files,
            params=params,
            headers={"Authorization": "Bearer test-token"}
        )

        # Should be caught by validation
        assert response.status_code in [400, 422]

    def test_upload_missing_file(self, client):
        """Test upload without file."""
        params = {"doc_type": "gst"}

        response = client.post(
            "/api/v1/vault/upload",
            params=params,
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
