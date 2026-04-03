"""Redis client for caching and task queue operations."""
from __future__ import annotations

import os
from typing import Any

import structlog

logger = structlog.get_logger()

_redis_client = None


def get_redis_client():
    """Get or create Redis client. Returns None if Redis is unavailable (graceful degradation)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        url = os.getenv("REDIS_URL", "")
        if not url:
            logger.warning("redis_url_missing", detail="REDIS_URL env var not set")
            return None
        _redis_client = redis.from_url(url, decode_responses=True, socket_connect_timeout=3)
        _redis_client.ping()
        logger.info("redis_connected", url=url[:30] + "...")
        return _redis_client
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        return None


class RedisCache:
    """Simple Redis cache wrapper with graceful degradation."""

    def __init__(self) -> None:
        self._client = get_redis_client()

    def get(self, key: str) -> Any | None:
        if not self._client:
            return None
        try:
            import json
            val = self._client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.warning("redis_get_failed", key=key, error=str(e))
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        if not self._client:
            return False
        try:
            import json
            self._client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning("redis_set_failed", key=key, error=str(e))
            return False

    def delete(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning("redis_delete_failed", key=key, error=str(e))
            return False

    def exists(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.warning("redis_exists_failed", key=key, error=str(e))
            return False
