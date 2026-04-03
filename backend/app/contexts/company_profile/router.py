from uuid import UUID

from fastapi import APIRouter, Depends

from app.contexts.user_management.schemas import UserResponse
from app.dependencies import get_current_company_id, get_current_user_id

from .schemas import (
    CompanyProfileCreate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
)
from .service import CompanyProfileService

router = APIRouter(prefix="/company", tags=["company_profile"])


@router.get("/company/profile", response_model=CompanyProfileResponse)
async def get_profile(
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
) -> CompanyProfileResponse:
    """Get current company profile."""
    service = CompanyProfileService()
    return await service.get_profile(company_id)


@router.post("/company/profile", response_model=CompanyProfileResponse)
async def create_profile(
    data: CompanyProfileCreate,
    current_user: UserResponse = Depends(get_current_user_id),
) -> CompanyProfileResponse:
    """Create company profile."""
    service = CompanyProfileService()
    return await service.create_profile(current_user.id, data)


@router.patch("/company/profile", response_model=CompanyProfileResponse)
async def update_profile(
    data: CompanyProfileUpdate,
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
) -> CompanyProfileResponse:
    """Update company profile."""
    service = CompanyProfileService()
    return await service.update_profile(company_id, data)


@router.get("/company/profile/lang")
async def get_preferred_lang(
    _current_user: UserResponse = Depends(get_current_user_id),
    company_id: UUID = Depends(get_current_company_id),
) -> dict[str, str]:
    """Get preferred language (used by frontend Tamil toggle)."""
    service = CompanyProfileService()
    lang = await service.get_preferred_lang(company_id)
    return {"lang": lang}
