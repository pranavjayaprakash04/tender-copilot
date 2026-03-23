from __future__ import annotations

from fastapi import Request
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import AsyncSessionFactory
from app.shared.logger import get_logger

logger = get_logger()

SKIP_PATHS = {
    "/health", "/docs", "/redoc", "/openapi.json",
    "/api/v1/webhook",
}


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in SKIP_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            request.state.company_id = None
            return await call_next(request)

        # Fixed: use AsyncSessionFactory directly with proper async context manager
        # instead of the generator-based get_async_session() which leaks connections
        # when broken out of with `break`
        try:
            async with AsyncSessionFactory() as session:
                result = await session.execute(
                    text("SELECT id FROM companies WHERE user_id = :user_id LIMIT 1"),
                    {"user_id": user_id},
                )
                row = result.fetchone()
                request.state.company_id = str(row[0]) if row else None
        except Exception as e:
            logger.error("tenant_middleware_error", error=str(e))
            request.state.company_id = None

        return await call_next(request)
