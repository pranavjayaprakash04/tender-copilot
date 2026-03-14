from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.contexts.partner_portal.repository import CAPartnerRepository
from app.contexts.partner_portal.schemas import (
    BulkAlertRequest,
    BulkBidRequest,
    CADashboardResponse,
    ManagedCompanyResponse,
)
from app.contexts.partner_portal.service import CAPartnerService
from app.dependencies import get_current_user_id
from app.shared.exceptions import ConflictException, NotFoundException

router = APIRouter(prefix="/partner", tags=["partner_portal"])


async def get_ca_service(session: AsyncSession = Depends(get_async_session)) -> CAPartnerService:
    """Get CA partner service instance."""
    repository = CAPartnerRepository(session)
    return CAPartnerService(repository)


@router.get("/dashboard", response_model=CADashboardResponse)
async def get_dashboard(
    ca_id: UUID,
    service: CAPartnerService = Depends(get_ca_service),
    _current_user=Depends(get_current_user_id),
) -> CADashboardResponse:
    """Get CA dashboard with company statistics."""
    try:
        return await service.get_dashboard(ca_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/companies", response_model=ManagedCompanyResponse)
async def add_managed_company(
    company_id: UUID,
    ca_id: UUID,
    service: CAPartnerService = Depends(get_ca_service),
    _current_user=Depends(get_current_user_id),
) -> ManagedCompanyResponse:
    """Add a company to CA's managed list."""
    try:
        return await service.add_company(ca_id, company_id)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/companies/{company_id}")
async def remove_managed_company(
    company_id: UUID,
    ca_id: UUID,
    service: CAPartnerService = Depends(get_ca_service),
    _current_user=Depends(get_current_user_id),
) -> dict:
    """Remove a company from CA's managed list."""
    try:
        await service.remove_company(ca_id, company_id)
        return {"message": "Company removed successfully"}
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/bulk/bids")
async def bulk_trigger_bids(
    req: BulkBidRequest,
    ca_id: UUID,
    service: CAPartnerService = Depends(get_ca_service),
    _current_user=Depends(get_current_user_id),
) -> dict:
    """Bulk trigger bid generation for managed companies."""
    try:
        return await service.bulk_trigger_bids(ca_id, req)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/bulk/alerts")
async def bulk_send_alerts(
    req: BulkAlertRequest,
    ca_id: UUID,
    service: CAPartnerService = Depends(get_ca_service),
    _current_user=Depends(get_current_user_id),
) -> dict:
    """Bulk send alerts to managed companies."""
    try:
        return await service.bulk_send_alert(ca_id, req)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/companies", response_model=list[ManagedCompanyResponse])
async def list_managed_companies(
    ca_id: UUID,
    service: CAPartnerService = Depends(get_ca_service),
    _current_user=Depends(get_current_user_id),
) -> list[ManagedCompanyResponse]:
    """List all managed companies for a CA partner."""
    try:
        dashboard = await service.get_dashboard(ca_id)
        return dashboard.companies
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
