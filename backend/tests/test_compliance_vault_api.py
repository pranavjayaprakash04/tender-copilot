"""Integration tests for compliance vault API endpoints."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestComplianceVaultAPI:
    """Test compliance vault API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

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
        assert response.json()["status"] == "healthy"

    def test_upload_document_unauthorized(self, client):
        """Test upload without authentication."""
        response = client.post("/api/v1/vault/upload")
        assert response.status_code == 401

    @patch('app.contexts.compliance_vault.router.get_db_session')
    @patch('app.contexts.compliance_vault.router.get_current_company_id')
    def test_upload_document_success(self, mock_company_id, mock_session, client, auth_headers):
        """Test successful document upload."""
        mock_company_id.return_value = uuid4()

        # Mock dependencies
        mock_session.return_value = AsyncMock()

        # Create test file
        files = {"file": ("test.pdf", b"pdf content", "application/pdf")}
        params = {"doc_type": "gst", "expires_at": "2024-12-31T23:59:59"}

        with patch('app.contexts.compliance_vault.router.ComplianceVaultService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance

            # Mock service response
            mock_doc_response = {
                "id": str(uuid4()),
                "filename": "test.pdf",
                "doc_type": "gst",
                "version": 1,
                "is_current": True
            }
            mock_service_instance.upload_document.return_value = mock_doc_response

            response = client.post(
                "/api/v1/vault/upload",
                files=files,
                params=params,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["filename"] == "test.pdf"
            assert data["data"]["doc_type"] == "gst"

    @patch('app.contexts.compliance_vault.router.get_db_session')
    @patch('app.contexts.compliance_vault.router.get_current_company_id')
    def test_list_documents(self, mock_company_id, mock_session, client, auth_headers):
        """Test listing documents."""
        mock_company_id.return_value = uuid4()
        mock_session.return_value = AsyncMock()

        with patch('app.contexts.compliance_vault.router.ComplianceVaultService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance

            # Mock service response
            mock_service_instance.list_documents.return_value = (
                {"documents": [], "total": 0, "expiring_soon": [], "expired": []},
                0
            )

            response = client.get("/api/v1/vault/documents", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "pagination" in data

    @patch('app.contexts.compliance_vault.router.get_db_session')
    @patch('app.contexts.compliance_vault.router.get_current_company_id')
    def test_classify_document(self, mock_company_id, mock_session, client, auth_headers):
        """Test document classification."""
        mock_company_id.return_value = uuid4()
        mock_session.return_value = AsyncMock()

        with patch('app.contexts.compliance_vault.router.ComplianceVaultService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance

            # Mock service response
            mock_service_instance.classify_document.return_value = {
                "doc_type": "gst",
                "confidence": 0.95,
                "reasoning": "Document contains GST registration"
            }

            payload = {
                "filename": "gst_certificate.pdf",
                "content_preview": "GST Registration Certificate"
            }

            response = client.post(
                "/api/v1/vault/classify",
                json=payload,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["doc_type"] == "gst"
            assert data["data"]["confidence"] == 0.95

    @patch('app.contexts.compliance_vault.router.get_db_session')
    @patch('app.contexts.compliance_vault.router.get_current_company_id')
    def test_get_document_stats(self, mock_company_id, mock_session, client, auth_headers):
        """Test getting document statistics."""
        mock_company_id.return_value = uuid4()
        mock_session.return_value = AsyncMock()

        with patch('app.contexts.compliance_vault.router.ComplianceVaultService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance

            # Mock service response
            mock_service_instance.get_document_stats.return_value = {
                "total_documents": 10,
                "current_documents": 8,
                "expired_documents": 2,
                "expiring_soon_documents": 3,
                "by_type": {"gst": 3, "pan": 2}
            }

            response = client.get("/api/v1/vault/stats", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["total_documents"] == 10
            assert data["data"]["current_documents"] == 8

    @patch('app.contexts.compliance_vault.router.get_db_session')
    @patch('app.contexts.compliance_vault.router.get_current_company_id')
    def test_analyze_tender_requirements(self, mock_company_id, mock_session, client, auth_headers):
        """Test analyzing tender requirements."""
        mock_company_id.return_value = uuid4()
        mock_session.return_value = AsyncMock()

        with patch('app.contexts.compliance_vault.router.ComplianceVaultService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance

            # Mock service response
            mock_service_instance.get_required_documents_for_tender.return_value = [
                "gst", "pan", "experience_certificate"
            ]

            params = {
                "tender_title": "Construction Project",
                "tender_requirements": "GST registration, experience certificate required"
            }

            response = client.post(
                "/api/v1/vault/tenders/analyze-requirements",
                params=params,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == 3
            assert "gst" in data["data"]

    def test_upload_invalid_file_type(self, client, auth_headers):
        """Test upload with invalid file type."""
        files = {"file": ("test.txt", b"text content", "text/plain")}
        params = {"doc_type": "gst"}

        response = client.post(
            "/api/v1/vault/upload",
            files=files,
            params=params,
            headers=auth_headers
        )

        # Should be caught by validation
        assert response.status_code in [400, 422]

    def test_upload_missing_file(self, client, auth_headers):
        """Test upload without file."""
        params = {"doc_type": "gst"}

        response = client.post(
            "/api/v1/vault/upload",
            params=params,
            headers=auth_headers
        )

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
