from __future__ import annotations

from supabase import create_client
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.shared.logger import get_logger

logger = get_logger()

SKIP_PATHS = {
    "/health", "/docs", "/redoc", "/openapi.json",
    "/api/v1/webhook",
}

_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in SKIP_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            request.state.user_id = None
            request.state.company_id = None
            return await call_next(request)

        token = auth_header.split(" ", 1)[1]

        try:
            response = _supabase.auth.get_user(token)
            user = response.user if response else None
            request.state.user_id = user.id if user else None
        except Exception as e:
            logger.warning("auth_token_invalid", error=str(e))
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        # Look up company_id for this user via user_id column
        request.state.company_id = None
        if request.state.user_id:
            try:
                result = (
                    _supabase
                    .table("companies")
                    .select("id")
                    .eq("user_id", request.state.user_id)
                    .limit(1)
                    .execute()
                )
                if result.data and len(result.data) > 0:
                    request.state.company_id = result.data[0]["id"]
            except Exception as e:
                logger.warning("company_lookup_failed", user_id=request.state.user_id, error=str(e))

        return await call_next(request)
