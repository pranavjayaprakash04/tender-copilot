from __future__ import annotations
import base64
import jwt
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
            # Supabase JWT secret is base64url-encoded — decode to raw bytes before verifying
            secret = base64.b64decode(settings.SUPABASE_JWT_SECRET + "==")
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            request.state.user_id = payload.get("sub")
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token expired"})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        return await call_next(request)
