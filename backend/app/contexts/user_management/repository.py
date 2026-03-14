from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.logger import get_logger

from .models import User
from .schemas import UserCreate

logger = get_logger()


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        """Create new user."""
        user = User(
            id=UUID(),
            email=data.email,
            role=data.role,
            subscription_tier="free",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        logger.info(f"Created user: {user.id}")
        return user

    async def update_subscription(self, user_id: UUID, tier: str) -> User:
        """Update user subscription tier."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        user.subscription_tier = tier
        user.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(user)

        logger.info(f"Updated subscription for user {user_id} to {tier}")
        return user
