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

# Use service role key to verify any user token via Supabase API
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
            return await call_next(request)

        token = auth_header.split(" ", 1)[1]
        try:
            response = _supabase.auth.get_user(token)
            request.state.user_id = response.user.id if response.user else None
        except Exception as e:
            logger.warning("auth_token_invalid", error=str(e))
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        return await call_next(request)
