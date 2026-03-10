from __future__ import annotations

import structlog
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = structlog.get_logger()


class Base(DeclarativeBase):
    """Base model class for all SQLAlchemy models."""
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session factory
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncSession:
    """Dependency to get async database session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception as e:
            logger.error("database_session_error", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they are registered with Base
            from app.contexts.tender_discovery.models import Tender  # noqa
            from app.contexts.bid_generation.models import Bid  # noqa
            from app.contexts.bid_lifecycle.models import BidOutcome, LossAnalysis  # noqa
            from app.contexts.compliance_vault.models import VaultDocument, VaultDocumentMapping  # noqa
            from app.contexts.company_profile.models import Company  # noqa
            from app.contexts.user_management.models import User, CAManagedCompany  # noqa
            from app.contexts.alert_engine.models import AlertRule  # noqa
            from app.contexts.whatsapp_gateway.models import WhatsAppSession  # noqa
            from app.contexts.partner_portal.models import Subscription  # noqa

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("database_connections_closed")
