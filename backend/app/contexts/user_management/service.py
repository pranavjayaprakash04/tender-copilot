from uuid import UUID

from app.shared.exceptions import NotFoundException
from app.shared.logger import get_logger

from .repository import UserRepository
from .schemas import (
    SubscriptionResponse,
    UserCreate,
    UserResponse,
)

logger = get_logger()


class UserService:
    def __init__(self, repository: UserRepository | None = None):
        self.repository = repository or UserRepository()

    async def get_user(self, user_id: UUID) -> UserResponse:
        """Get user by ID."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise NotFoundException(f"User {user_id} not found")

        return UserResponse.model_validate(user)

    async def create_user(self, data: UserCreate) -> UserResponse:
        """Create new user."""
        # Check if user already exists
        existing = await self.repository.get_by_email(data.email)
        if existing:
            logger.warning(f"User already exists: {data.email}")
            raise ValueError("User with this email already exists")

        user = await self.repository.create(data)
        logger.info(f"Created user: {user.id}")

        return UserResponse.model_validate(user)

    async def get_subscription(self, user_id: UUID) -> SubscriptionResponse:
        """Get user subscription status."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise NotFoundException(f"User {user_id} not found")

        return SubscriptionResponse(
            user_id=user.id,
            plan=user.subscription_tier,
            status="active" if user.is_active else "inactive",
            renewal_date=None,  # TODO: Add renewal date tracking
        )

    async def update_subscription_tier(self, user_id: UUID, tier: str) -> UserResponse:
        """Update user subscription tier."""
        user = await self.repository.update_subscription(user_id, tier)
        logger.info(f"Updated subscription for user {user_id} to {tier}")

        return UserResponse.model_validate(user)
