import structlog
from fastapi import Request

from app.shared.exceptions import AuthorizationException

logger = structlog.get_logger()

async def tenant_middleware(request: Request, call_next):
    """Middleware to inject company_id from JWT token for multi-tenancy."""

    # Skip tenant injection for health check and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    # Get user info from auth middleware
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise AuthorizationException("User not authenticated")

    try:
        # TODO: Extract company_id from JWT token or user session
        # For now, we'll use a mock company_id
        # This will be implemented when we integrate proper multi-tenancy

        # Mock company for development
        request.state.company_id = "mock-company-id"

        logger.info(
            "tenant_context_set",
            trace_id=getattr(request.state, "trace_id", None),
            user_id=user_id,
            company_id=request.state.company_id,
        )

    except Exception as e:
        logger.error(
            "tenant_context_failed",
            trace_id=getattr(request.state, "trace_id", None),
            user_id=user_id,
            error=str(e),
        )
        raise AuthorizationException("Failed to establish tenant context")

    return await call_next(request)
