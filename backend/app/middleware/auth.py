import structlog
from fastapi import Request

from app.shared.exceptions import AuthenticationException

logger = structlog.get_logger()

async def auth_middleware(request: Request, call_next):
    """Middleware to validate JWT tokens from Supabase."""

    # Skip auth for health check and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationException("Missing or invalid Authorization header")

    try:
        # TODO: Validate JWT token with Supabase
        # For now, we'll skip actual validation and add user_id to state
        # This will be implemented when we integrate Supabase Auth

        # Mock user for development
        request.state.user_id = "mock-user-id"
        request.state.user_email = "mock@example.com"
        request.state.user_role = "msme_owner"

        logger.info(
            "auth_success",
            trace_id=getattr(request.state, "trace_id", None),
            user_id=request.state.user_id,
        )

    except Exception as e:
        logger.error(
            "auth_failed",
            trace_id=getattr(request.state, "trace_id", None),
            error=str(e),
        )
        raise AuthenticationException("Invalid authentication token")

    return await call_next(request)
