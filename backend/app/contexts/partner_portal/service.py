from __future__ import annotations

from uuid import UUID

import structlog

from app.contexts.partner_portal.repository import CAPartnerRepository
from app.contexts.partner_portal.schemas import (
    BulkAlertRequest,
    BulkBidRequest,
    CADashboardResponse,
    ManagedCompanyResponse,
)
from app.shared.exceptions import ConflictException, NotFoundException

logger = structlog.get_logger()


class CAPartnerService:
    """Service for CA Partner operations."""

    def __init__(self, repository: CAPartnerRepository) -> None:
        self.repository = repository

    async def get_dashboard(self, ca_id: UUID) -> CADashboardResponse:
        """Get CA dashboard with company statistics."""
        try:
            # Verify CA exists
            ca_partner = await self.repository.get_ca_by_id(ca_id)
            if not ca_partner:
                raise NotFoundException("CA partner")

            # Get managed companies
            managed_companies = await self.repository.get_managed_companies(ca_id)

            # Convert to response format (mock data for now since we don't have company details)
            company_responses = []
            total_active_bids = 0
            total_won_bids = 0

            for managed_company in managed_companies:
                # Mock data - in real implementation, fetch from bid lifecycle
                active_bids = 0  # TODO: Get from bid lifecycle context
                won_bids = 0     # TODO: Get from bid lifecycle context
                pending_tenders = 0  # TODO: Get from tender discovery context

                total_active_bids += active_bids
                total_won_bids += won_bids

                company_response = ManagedCompanyResponse(
                    id=managed_company.id,
                    company_id=managed_company.company_id,
                    ca_id=managed_company.ca_id,
                    access_level=managed_company.access_level,
                    company_name=f"Company {managed_company.company_id}",  # Mock name
                    active_bids=active_bids,
                    pending_tenders=pending_tenders,
                    created_at=managed_company.created_at,
                )
                company_responses.append(company_response)

            return CADashboardResponse(
                ca_id=ca_id,
                total_companies=len(managed_companies),
                total_active_bids=total_active_bids,
                total_won_bids=total_won_bids,
                companies=company_responses,
            )
        except NotFoundException:
            raise
        except Exception as e:
            logger.error("get_dashboard_error", ca_id=str(ca_id), error=str(e))
            raise

    async def add_company(self, ca_id: UUID, company_id: UUID) -> ManagedCompanyResponse:
        """Add a company to CA's managed list."""
        try:
            # Verify CA exists
            ca_partner = await self.repository.get_ca_by_id(ca_id)
            if not ca_partner:
                raise NotFoundException("CA partner")

            # Check if company is already managed
            is_already_managed = await self.repository.check_company_managed(ca_id, company_id)
            if is_already_managed:
                raise ConflictException("Company is already managed by this CA partner")

            # Add company to managed list
            managed_company = await self.repository.add_managed_company(
                ca_id, company_id, "full"
            )

            return ManagedCompanyResponse(
                id=managed_company.id,
                company_id=managed_company.company_id,
                ca_id=managed_company.ca_id,
                access_level=managed_company.access_level,
                company_name=f"Company {company_id}",  # Mock name
                active_bids=0,  # Mock data
                pending_tenders=0,  # Mock data
                created_at=managed_company.created_at,
            )
        except (NotFoundException, ConflictException):
            raise
        except Exception as e:
            logger.error(
                "add_company_error", ca_id=str(ca_id), company_id=str(company_id), error=str(e)
            )
            raise

    async def remove_company(self, ca_id: UUID, company_id: UUID) -> None:
        """Remove a company from CA's managed list."""
        try:
            # Verify CA exists
            ca_partner = await self.repository.get_ca_by_id(ca_id)
            if not ca_partner:
                raise NotFoundException("CA partner")

            # Remove company
            await self.repository.remove_managed_company(ca_id, company_id)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(
                "remove_company_error", ca_id=str(ca_id), company_id=str(company_id), error=str(e)
            )
            raise

    async def bulk_trigger_bids(self, ca_id: UUID, req: BulkBidRequest) -> dict:
        """Bulk trigger bid generation for managed companies."""
        try:
            # Verify CA exists
            ca_partner = await self.repository.get_ca_by_id(ca_id)
            if not ca_partner:
                raise NotFoundException("CA partner")

            # Get managed company IDs
            managed_company_ids = await self.repository.get_managed_company_ids(ca_id)

            # Filter requested companies to only those managed by CA
            valid_company_ids = [
                company_id for company_id in req.company_ids
                if company_id in managed_company_ids
            ]

            skipped_count = len(req.company_ids) - len(valid_company_ids)
            dispatched_count = 0

            # Dispatch bid generation tasks for valid companies
            for company_id in valid_company_ids:
                try:
                    # TODO: Dispatch to Celery bid_generation task
                    # bid_generation_task.delay(str(company_id), str(req.tender_id))
                    logger.info(
                        "bid_generation_dispatched",
                        ca_id=str(ca_id),
                        company_id=str(company_id),
                        tender_id=str(req.tender_id),
                    )
                    dispatched_count += 1
                except Exception as e:
                    logger.error(
                        "bid_generation_dispatch_error",
                        ca_id=str(ca_id),
                        company_id=str(company_id),
                        tender_id=str(req.tender_id),
                        error=str(e),
                    )

            return {"dispatched": dispatched_count, "skipped": skipped_count}
        except NotFoundException:
            raise
        except Exception as e:
            logger.error("bulk_trigger_bids_error", ca_id=str(ca_id), error=str(e))
            raise

    async def bulk_send_alert(self, ca_id: UUID, req: BulkAlertRequest) -> dict:
        """Bulk send alerts to managed companies."""
        try:
            # Verify CA exists
            ca_partner = await self.repository.get_ca_by_id(ca_id)
            if not ca_partner:
                raise NotFoundException("CA partner")

            # Get managed company IDs
            managed_company_ids = await self.repository.get_managed_company_ids(ca_id)

            # Filter requested companies to only those managed by CA
            valid_company_ids = [
                company_id for company_id in req.company_ids
                if company_id in managed_company_ids
            ]

            sent_count = 0

            # Send alerts to valid companies
            for company_id in valid_company_ids:
                try:
                    # TODO: Log alert in alert_engine
                    logger.info(
                        "alert_sent",
                        ca_id=str(ca_id),
                        company_id=str(company_id),
                        message=req.message,
                        alert_type=req.alert_type,
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(
                        "alert_send_error",
                        ca_id=str(ca_id),
                        company_id=str(company_id),
                        message=req.message,
                        alert_type=req.alert_type,
                        error=str(e),
                    )

            return {"sent": sent_count}
        except NotFoundException:
            raise
        except Exception as e:
            logger.error("bulk_send_alert_error", ca_id=str(ca_id), error=str(e))
            raise
