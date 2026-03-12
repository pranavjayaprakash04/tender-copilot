
from fastapi import APIRouter, Depends

from app.contexts.user_management.schemas import UserResponse
from app.dependencies import get_current_user_id

from .schemas import SubscriptionResponse
from .service import UserService

router = APIRouter(prefix="/users", tags=["user_management"])


@router.get("/users/me", response_model=UserResponse)
async def get_current_user(
    current_user: UserResponse = Depends(get_current_user_id),
) -> UserResponse:
    """Get current user profile."""
    service = UserService()
    return await service.get_user(current_user.id)


@router.get("/users/me/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: UserResponse = Depends(get_current_user_id),
) -> SubscriptionResponse:
    """Get subscription status."""
    service = UserService()
    return await service.get_subscription(current_user.id)


@router.patch("/users/me/subscription", response_model=UserResponse)
async def update_subscription_tier(
    tier: str,
    current_user: UserResponse = Depends(get_current_user_id),
) -> UserResponse:
    """Update subscription plan (Razorpay webhook will call this)."""
    service = UserService()
    return await service.update_subscription_tier(current_user.id, tier)
