"""Company profile repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.company_profile.models import Company


class CompanyRepository:
    """Repository for company operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, company_id: UUID) -> Company | None:
        """Get company by ID."""
        # Placeholder implementation
        return None
