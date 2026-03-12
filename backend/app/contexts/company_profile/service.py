from uuid import UUID

from app.shared.exceptions import NotFoundException
from app.shared.logger import logger

from .repository import CompanyProfileRepository
from .schemas import (
    CompanyProfileCreate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
)


class CompanyProfileService:
    def __init__(self, repository: CompanyProfileRepository | None = None):
        self.repository = repository or CompanyProfileRepository()

    async def get_profile(self, company_id: UUID) -> CompanyProfileResponse:
        """Get company profile by ID."""
        profile = await self.repository.get_by_company_id(company_id)
        if not profile:
            logger.warning(f"Company profile not found: {company_id}")
            raise NotFoundException(f"Company profile {company_id} not found")

        return CompanyProfileResponse.model_validate(profile)

    async def create_profile(
        self, user_id: UUID, data: CompanyProfileCreate
    ) -> CompanyProfileResponse:
        """Create new company profile."""
        # Check if profile already exists for user
        existing = await self.repository.get_by_user_id(user_id)
        if existing:
            logger.warning(f"Profile already exists for user: {user_id}")
            raise ValueError("Profile already exists for this user")

        profile = await self.repository.create(user_id, data)
        logger.info(f"Created company profile: {profile.id} for user: {user_id}")

        return CompanyProfileResponse.model_validate(profile)

    async def update_profile(
        self, company_id: UUID, data: CompanyProfileUpdate
    ) -> CompanyProfileResponse:
        """Update company profile."""
        profile = await self.repository.get_by_company_id(company_id)
        if not profile:
            logger.warning(f"Company profile not found: {company_id}")
            raise NotFoundException(f"Company profile {company_id} not found")

        updated = await self.repository.update(company_id, data)
        logger.info(f"Updated company profile: {company_id}")

        return CompanyProfileResponse.model_validate(updated)

    async def get_preferred_lang(self, company_id: UUID) -> str:
        """Get preferred language for company."""
        profile = await self.repository.get_by_company_id(company_id)
        if not profile:
            logger.warning(f"Company profile not found: {company_id}")
            raise NotFoundException(f"Company profile {company_id} not found")

        return profile.preferred_lang or "en"
