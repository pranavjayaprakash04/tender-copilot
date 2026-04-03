from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.partner_portal.models import CAManagedCompany, CAPartner
from app.shared.exceptions import NotFoundException

logger = structlog.get_logger()


class CAPartnerRepository:
    """Repository for CA Partner operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_ca_by_id(self, ca_id: UUID) -> CAPartner | None:
        """Get CA partner by ID."""
        try:
            stmt = select(CAPartner).where(CAPartner.id == ca_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("get_ca_by_id_error", ca_id=str(ca_id), error=str(e))
            raise

    async def get_ca_by_email(self, email: str) -> CAPartner | None:
        """Get CA partner by email."""
        try:
            stmt = select(CAPartner).where(CAPartner.email == email)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("get_ca_by_email_error", email=email, error=str(e))
            raise

    async def create_ca(self, data: dict) -> CAPartner:
        """Create a new CA partner."""
        try:
            ca_partner = CAPartner(**data)
            self.session.add(ca_partner)
            await self.session.flush()
            await self.session.refresh(ca_partner)
            return ca_partner
        except Exception as e:
            logger.error("create_ca_error", error=str(e))
            await self.session.rollback()
            raise

    async def get_managed_companies(self, ca_id: UUID) -> list[CAManagedCompany]:
        """Get all companies managed by a CA partner."""
        try:
            stmt = select(CAManagedCompany).where(CAManagedCompany.ca_id == ca_id)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("get_managed_companies_error", ca_id=str(ca_id), error=str(e))
            raise

    async def add_managed_company(
        self, ca_id: UUID, company_id: UUID, access_level: str
    ) -> CAManagedCompany:
        """Add a company to CA's managed list."""
        try:
            managed_company = CAManagedCompany(
                ca_id=ca_id, company_id=company_id, access_level=access_level
            )
            self.session.add(managed_company)
            await self.session.flush()
            await self.session.refresh(managed_company)
            return managed_company
        except Exception as e:
            logger.error(
                "add_managed_company_error",
                ca_id=str(ca_id),
                company_id=str(company_id),
                error=str(e),
            )
            await self.session.rollback()
            raise

    async def remove_managed_company(self, ca_id: UUID, company_id: UUID) -> None:
        """Remove a company from CA's managed list."""
        try:
            stmt = select(CAManagedCompany).where(
                CAManagedCompany.ca_id == ca_id, CAManagedCompany.company_id == company_id
            )
            result = await self.session.execute(stmt)
            managed_company = result.scalar_one_or_none()

            if not managed_company:
                raise NotFoundException("Managed company relationship")

            await self.session.delete(managed_company)
            await self.session.flush()
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(
                "remove_managed_company_error",
                ca_id=str(ca_id),
                company_id=str(company_id),
                error=str(e),
            )
            await self.session.rollback()
            raise

    async def get_managed_company_ids(self, ca_id: UUID) -> list[UUID]:
        """Get list of company IDs managed by a CA partner."""
        try:
            stmt = select(CAManagedCompany.company_id).where(CAManagedCompany.ca_id == ca_id)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("get_managed_company_ids_error", ca_id=str(ca_id), error=str(e))
            raise

    async def check_company_managed(self, ca_id: UUID, company_id: UUID) -> bool:
        """Check if a company is managed by the CA partner."""
        try:
            stmt = select(CAManagedCompany).where(
                CAManagedCompany.ca_id == ca_id, CAManagedCompany.company_id == company_id
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(
                "check_company_managed_error",
                ca_id=str(ca_id),
                company_id=str(company_id),
                error=str(e),
            )
            raise
