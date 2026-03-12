from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# from app.contexts.bid_intelligence.router import router as bid_intelligence_router
# from app.contexts.company_profile.router import router as company_profile_router
# from app.contexts.user_management.router import router as user_management_router
# from app.contexts.whatsapp_gateway.router import router as whatsapp_gateway_router
# from app.contexts.partner_portal.router import router as partner_portal_router
from app.contexts.alert_engine.router import router as alert_engine_router
from app.contexts.bid_lifecycle.router import router as bid_lifecycle_router

from app.contexts.tender_intelligence.router import router as tender_intelligence_router
from app.contexts.tender_matching.router import router as tender_matching_router
from app.contexts.tender_matching.embedding_router import router as embedding_router
from app.contexts.compliance_vault.router import router as compliance_vault_router

# Import routers (will be created in subsequent phases)
from app.contexts.tender_discovery.router import router as tender_discovery_router
from app.database import close_db, init_db
from app.middleware.auth import auth_middleware
from app.middleware.error_handler import global_exception_handler
from app.middleware.logging import logging_middleware
from app.middleware.tenant import tenant_middleware
from app.shared.exceptions import AppException

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("application_startup", environment=settings.ENVIRONMENT)
    await init_db()
    logger.info("database_initialized")

    yield

    # Shutdown
    logger.info("application_shutdown")
    await close_db()


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Tender Copilot API",
        description="AI-powered government tender intelligence for Indian MSMEs",
        version="1.5.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.middleware("http")(logging_middleware)
    app.middleware("http")(auth_middleware)
    app.middleware("http")(tenant_middleware)

    # Add exception handler
    app.add_exception_handler(AppException, global_exception_handler)

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "environment": settings.ENVIRONMENT}

    # Register routers (will be uncommented as contexts are implemented)
    app.include_router(tender_discovery_router, prefix="/api/v1")
    app.include_router(tender_intelligence_router, prefix="/api/v1")
    app.include_router(tender_matching_router, prefix="/api/v1")
    app.include_router(embedding_router, prefix="/api/v1")
    app.include_router(compliance_vault_router, prefix="/api/v1")
    app.include_router(bid_lifecycle_router, prefix="/api/v1")
    app.include_router(alert_engine_router, prefix="/api/v1")
    # app.include_router(bid_intelligence_router, prefix="/api/v1")
    # app.include_router(company_profile_router, prefix="/api/v1")
    # app.include_router(user_management_router, prefix="/api/v1")
    # app.include_router(whatsapp_gateway_router, prefix="/api/v1")
    # app.include_router(partner_portal_router, prefix="/api/v1")

    return app


# Create app instance
app = create_app()
