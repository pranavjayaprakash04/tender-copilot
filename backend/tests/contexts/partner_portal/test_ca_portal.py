from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.contexts.partner_portal.models import CAPartner, CAManagedCompany
from app.contexts.partner_portal.schemas import (
    BulkAlertRequest,
    BulkBidRequest,
    CADashboardResponse,
    ManagedCompanyResponse,
)
from app.contexts.partner_portal.service import CAPartnerService
from app.shared.exceptions import ConflictException, NotFoundException


class TestCAPartnerPortal:
    """Test CA Partner Portal functionality."""

    @pytest.fixture
    def ca_id(self) -> UUID:
        """Test CA partner ID."""
        return UUID("12345678-1234-5678-1234-567812345678")

    @pytest.fixture
    def company_id(self) -> UUID:
        """Test company ID."""
        return UUID("87654321-4321-8765-4321-876543218765")

    @pytest.fixture
    def tender_id(self) -> UUID:
        """Test tender ID."""
        return UUID("fedcba98-8765-4321-cba9-876543210123")

    @pytest.fixture
    def mock_ca_partner(self, ca_id: UUID) -> CAPartner:
        """Mock CA partner."""
        ca_partner = MagicMock(spec=CAPartner)
        ca_partner.id = ca_id
        ca_partner.name = "Test CA Partner"
        ca_partner.email = "test@example.com"
        ca_partner.phone = "+1234567890"
        ca_partner.icai_number = "CA123456"
        ca_partner.subscription_tier = "ca_partner"
        ca_partner.is_active = True
        ca_partner.created_at = datetime.now(timezone.utc)
        ca_partner.updated_at = datetime.now(timezone.utc)
        return ca_partner

    @pytest.fixture
    def mock_managed_company(self, ca_id: UUID, company_id: UUID) -> CAManagedCompany:
        """Mock managed company."""
        managed_company = MagicMock(spec=CAManagedCompany)
        managed_company.id = UUID("11111111-1111-1111-1111-111111111111")
        managed_company.ca_id = ca_id
        managed_company.company_id = company_id
        managed_company.access_level = "full"
        managed_company.created_at = datetime.now(timezone.utc)
        return managed_company

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Mock CA partner repository."""
        return AsyncMock()

    @pytest.fixture
    def ca_service(self, mock_repository: AsyncMock) -> CAPartnerService:
        """CA partner service with mocked repository."""
        return CAPartnerService(mock_repository)

    async def test_get_dashboard_returns_companies(
        self, ca_service: CAPartnerService, ca_id: UUID, mock_ca_partner: CAPartner, 
        mock_managed_company: CAManagedCompany, mock_repository: AsyncMock
    ) -> None:
        """Test getting dashboard returns companies."""
        # Setup
        mock_repository.get_ca_by_id.return_value = mock_ca_partner
        mock_repository.get_managed_companies.return_value = [mock_managed_company]

        # Execute
        result = await ca_service.get_dashboard(ca_id)

        # Verify
        assert isinstance(result, CADashboardResponse)
        assert result.ca_id == ca_id
        assert result.total_companies == 1
        assert result.total_active_bids == 0
        assert result.total_won_bids == 0
        assert len(result.companies) == 1
        assert result.companies[0].company_id == mock_managed_company.company_id
        assert result.companies[0].access_level == mock_managed_company.access_level

        # Verify repository calls
        mock_repository.get_ca_by_id.assert_called_once_with(ca_id)
        mock_repository.get_managed_companies.assert_called_once_with(ca_id)

    async def test_add_managed_company_success(
        self, ca_service: CAPartnerService, ca_id: UUID, company_id: UUID,
        mock_ca_partner: CAPartner, mock_managed_company: CAManagedCompany,
        mock_repository: AsyncMock
    ) -> None:
        """Test successfully adding a managed company."""
        # Setup
        mock_repository.get_ca_by_id.return_value = mock_ca_partner
        mock_repository.check_company_managed.return_value = False
        mock_repository.add_managed_company.return_value = mock_managed_company

        # Execute
        result = await ca_service.add_company(ca_id, company_id)

        # Verify
        assert isinstance(result, ManagedCompanyResponse)
        assert result.company_id == company_id
        assert result.ca_id == ca_id
        assert result.access_level == "full"

        # Verify repository calls
        mock_repository.get_ca_by_id.assert_called_once_with(ca_id)
        mock_repository.check_company_managed.assert_called_once_with(ca_id, company_id)
        mock_repository.add_managed_company.assert_called_once_with(ca_id, company_id, "full")

    async def test_add_duplicate_company_raises_conflict(
        self, ca_service: CAPartnerService, ca_id: UUID, company_id: UUID,
        mock_ca_partner: CAPartner, mock_repository: AsyncMock
    ) -> None:
        """Test adding duplicate company raises ConflictException."""
        # Setup
        mock_repository.get_ca_by_id.return_value = mock_ca_partner
        mock_repository.check_company_managed.return_value = True

        # Execute and verify
        with pytest.raises(ConflictException, match="Company is already managed"):
            await ca_service.add_company(ca_id, company_id)

        # Verify repository calls
        mock_repository.get_ca_by_id.assert_called_once_with(ca_id)
        mock_repository.check_company_managed.assert_called_once_with(ca_id, company_id)
        mock_repository.add_managed_company.assert_not_called()

    async def test_remove_managed_company_success(
        self, ca_service: CAPartnerService, ca_id: UUID, company_id: UUID,
        mock_ca_partner: CAPartner, mock_repository: AsyncMock
    ) -> None:
        """Test successfully removing a managed company."""
        # Setup
        mock_repository.get_ca_by_id.return_value = mock_ca_partner
        mock_repository.remove_managed_company.return_value = None

        # Execute
        await ca_service.remove_company(ca_id, company_id)

        # Verify repository calls
        mock_repository.get_ca_by_id.assert_called_once_with(ca_id)
        mock_repository.remove_managed_company.assert_called_once_with(ca_id, company_id)

    async def test_bulk_bid_dispatches_to_all_companies(
        self, ca_service: CAPartnerService, ca_id: UUID, company_id: UUID,
        tender_id: UUID, mock_ca_partner: CAPartner, mock_repository: AsyncMock
    ) -> None:
        """Test bulk bid dispatch to all managed companies."""
        # Setup
        mock_repository.get_ca_by_id.return_value = mock_ca_partner
        mock_repository.get_managed_company_ids.return_value = [company_id]
        req = BulkBidRequest(company_ids=[company_id], tender_id=tender_id)

        # Execute
        result = await ca_service.bulk_trigger_bids(ca_id, req)

        # Verify
        assert result["dispatched"] == 1
        assert result["skipped"] == 0

        # Verify repository calls
        mock_repository.get_ca_by_id.assert_called_once_with(ca_id)
        mock_repository.get_managed_company_ids.assert_called_once_with(ca_id)

    async def test_bulk_bid_skips_unmanaged_companies(
        self, ca_service: CAPartnerService, ca_id: UUID, company_id: UUID,
        tender_id: UUID, mock_ca_partner: CAPartner, mock_repository: AsyncMock
    ) -> None:
        """Test bulk bid skips unmanaged companies."""
        # Setup
        unmanaged_company_id = UUID("99999999-9999-9999-9999-999999999999")
        mock_repository.get_ca_by_id.return_value = mock_ca_partner
        mock_repository.get_managed_company_ids.return_value = [company_id]
        req = BulkBidRequest(company_ids=[company_id, unmanaged_company_id], tender_id=tender_id)

        # Execute
        result = await ca_service.bulk_trigger_bids(ca_id, req)

        # Verify
        assert result["dispatched"] == 1  # Only managed company
        assert result["skipped"] == 1   # Unmanaged company

        # Verify repository calls
        mock_repository.get_ca_by_id.assert_called_once_with(ca_id)
        mock_repository.get_managed_company_ids.assert_called_once_with(ca_id)

    async def test_bulk_alert_sends_to_all_companies(
        self, ca_service: CAPartnerService, ca_id: UUID, company_id: UUID,
        mock_ca_partner: CAPartner, mock_repository: AsyncMock
    ) -> None:
        """Test bulk alert sends to all managed companies."""
        # Setup
        mock_repository.get_ca_by_id.return_value = mock_ca_partner
        mock_repository.get_managed_company_ids.return_value = [company_id]
        req = BulkAlertRequest(
            company_ids=[company_id],
            message="Test alert",
            alert_type="info"
        )

        # Execute
        result = await ca_service.bulk_send_alert(ca_id, req)

        # Verify
        assert result["sent"] == 1

        # Verify repository calls
        mock_repository.get_ca_by_id.assert_called_once_with(ca_id)
        mock_repository.get_managed_company_ids.assert_called_once_with(ca_id)
