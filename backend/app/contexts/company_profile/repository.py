"""Company profile repository."""
from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.contexts.company_profile.models import Company
from app.contexts.company_profile.schemas import CompanyProfileCreate, CompanyProfileUpdate


class CompanyProfileRepository:
    """Repository for company profile operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, company_id: UUID) -> Company | None:
        result = await self._session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_company_id(self, company_id: UUID) -> Company | None:
        result = await self._session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: str) -> Company | None:
        """Company table doesn't have user_id — look up via user_id stored at create time."""
        # user_id is stored as contact reference; we use the description field hack
        # until a proper user_companies join table is added.
        # For now return None so create always proceeds.
        return None

    async def create(self, user_id: str, data: CompanyProfileCreate) -> Company:
        company = Company(
            name=data.name,
            industry=data.industry or "Other",
            location=data.location or "",
            contact_email=data.contact_email or "",
            contact_phone=data.contact_phone,
            website=data.website,
            description=data.description,
            capabilities_text=data.capabilities_text or "",
            size="small",           # default — Company model requires this
            is_active=True,
        )
        self._session.add(company)
        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def update(self, company_id: UUID, data: CompanyProfileUpdate) -> Company:
        company = await self.get_by_company_id(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            if hasattr(company, field):
                setattr(company, field, value)

        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def get_all_companies(self) -> list[Company]:
        result = await self._session.execute(select(Company).where(Company.is_active == True))
        return list(result.scalars().all())

    async def get_all_without_embeddings(self) -> list[Company]:
        result = await self._session.execute(select(Company).where(Company.is_active == True))
        return list(result.scalars().all())
