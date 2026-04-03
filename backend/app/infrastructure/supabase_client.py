"""Supabase client for authentication and database operations."""
from __future__ import annotations

import os
import structlog
from typing import Any

logger = structlog.get_logger()


def get_supabase_client():
    """Get Supabase client. Returns None if env vars not set (graceful degradation)."""
    try:
        from supabase import create_client, Client
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            logger.warning("supabase_env_missing", detail="SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
            return None
        return create_client(url, key)
    except Exception as e:
        logger.error("supabase_client_init_failed", error=str(e))
        return None


class SupabaseAuthClient:
    """Wrapper for Supabase auth operations."""

    def __init__(self) -> None:
        self._client = get_supabase_client()

    def verify_jwt(self, token: str) -> dict[str, Any] | None:
        """Verify a Supabase JWT token and return the payload."""
        if not self._client:
            return None
        try:
            import jwt as pyjwt
            jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "")
            if not jwt_secret:
                logger.warning("supabase_jwt_secret_missing")
                return None
            payload = pyjwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return payload
        except Exception as e:
            logger.warning("jwt_verification_failed", error=str(e))
            return None

    def get_user(self, token: str) -> dict[str, Any] | None:
        """Get user info from Supabase using access token."""
        if not self._client:
            return None
        try:
            response = self._client.auth.get_user(token)
            if response and response.user:
                return {
                    "id": str(response.user.id),
                    "email": response.user.email,
                    "metadata": response.user.user_metadata or {},
                }
            return None
        except Exception as e:
            logger.warning("get_user_failed", error=str(e))
            return None
