from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import (
    get_current_company_id,
    get_current_company_id_optional,
    get_current_user_id,
    get_db_session,
)
from .repository import CompanyProfileRepository
from .schemas import (
    CompanyProfileCreate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
)
from .service import CompanyProfileService

router = APIRouter(prefix="/company", tags=["company_profile"])


def get_service(session: AsyncSession = Depends(get_db_session)) -> CompanyProfileService:
    repo = CompanyProfileRepository(session)
    return CompanyProfileService(repo)


@router.get("/profile", response_model=CompanyProfileResponse | None)
async def get_profile(
    _current_user: str = Depends(get_current_user_id),
    company_id: str | None = Depends(get_current_company_id_optional),
    service: CompanyProfileService = Depends(get_service),
) -> CompanyProfileResponse | None:
    if not company_id:
        return None
    try:
        return await service.get_profile(UUID(company_id))
    except Exception:
        return None


@router.post("/profile", response_model=CompanyProfileResponse)
async def create_profile(
    data: CompanyProfileCreate,
    current_user_id: str = Depends(get_current_user_id),
    service: CompanyProfileService = Depends(get_service),
) -> CompanyProfileResponse:
    return await service.create_profile(UUID(current_user_id), data)


@router.patch("/profile", response_model=CompanyProfileResponse)
async def update_profile(
    data: CompanyProfileUpdate,
    _current_user: str = Depends(get_current_user_id),
    company_id: str = Depends(get_current_company_id),
    service: CompanyProfileService = Depends(get_service),
) -> CompanyProfileResponse:
    return await service.update_profile(UUID(company_id), data)


@router.get("/profile/lang")
async def get_preferred_lang(
    _current_user: str = Depends(get_current_user_id),
    company_id: str = Depends(get_current_company_id),
    service: CompanyProfileService = Depends(get_service),
) -> dict[str, str]:
    lang = await service.get_preferred_lang(UUID(company_id))
    return {"lang": lang}
