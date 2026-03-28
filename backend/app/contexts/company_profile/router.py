from uuid import UUID
from fastapi import APIRouter, Depends
from app.dependencies import (
    get_current_company_id,
    get_current_company_id_optional,
    get_current_user_id,
)
from .schemas import (
    CompanyProfileCreate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
)
from .service import CompanyProfileService

router = APIRouter(prefix="/company", tags=["company_profile"])


@router.get("/profile", response_model=CompanyProfileResponse | None)
async def get_profile(
    _current_user: str = Depends(get_current_user_id),
    company_id: str | None = Depends(get_current_company_id_optional),
) -> CompanyProfileResponse | None:
    """Get current company profile. Returns null for new users with no profile."""
    if not company_id:
        return None
    service = CompanyProfileService()
    try:
        return await service.get_profile(UUID(company_id))
    except Exception:
        return None


@router.post("/profile", response_model=CompanyProfileResponse)
async def create_profile(
    data: CompanyProfileCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> CompanyProfileResponse:
    """Create company profile for a new user."""
    service = CompanyProfileService()
    return await service.create_profile(UUID(current_user_id), data)


@router.patch("/profile", response_model=CompanyProfileResponse)
async def update_profile(
    data: CompanyProfileUpdate,
    _current_user: str = Depends(get_current_user_id),
    company_id: str = Depends(get_current_company_id),
) -> CompanyProfileResponse:
    """Update company profile."""
    service = CompanyProfileService()
    return await service.update_profile(UUID(company_id), data)


@router.get("/profile/lang")
async def get_preferred_lang(
    _current_user: str = Depends(get_current_user_id),
    company_id: str = Depends(get_current_company_id),
) -> dict[str, str]:
    """Get preferred language."""
    service = CompanyProfileService()
    lang = await service.get_preferred_lang(UUID(company_id))
    return {"lang": lang}
