"""Company profile repository."""

from __future__ import annotations

from typing import List

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.company_profile.models import Company


class CompanyProfileRepository:
    """Repository for company profile operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, company_id: UUID) -> Company | None:
        """Get company by ID."""
        # Placeholder implementation
        return None

    async def get_by_company_id(self, company_id: UUID) -> Company | None:
        """Get company profile by company ID."""
        # Placeholder implementation
        return None

    async def get_by_user_id(self, user_id: str) -> Company | None:
        """Get company profile by user ID."""
        # Placeholder implementation
        return None

    async def create(self, user_id: str, data) -> Company:
        """Create company profile."""
        # Placeholder implementation
        return Company()

    async def update(self, company_id: UUID, data) -> Company:
        """Update company profile."""
        # Placeholder implementation
        return Company()

    async def get_all_companies(self) -> List[Company]:
        """Get all companies."""
        # Placeholder implementation
        return []

    async def get_all_without_embeddings(self) -> List[Company]:
        """Get all companies without embeddings."""
        # Placeholder implementation
        return []
