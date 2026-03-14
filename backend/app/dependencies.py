from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.shared.lang_context import Lang, LangContext


def get_trace_id(request: Request) -> str:
    """Get trace ID from request state or generate new one."""
    return getattr(request.state, "trace_id", str(uuid.uuid4()))

def get_current_user_id(request: Request) -> str:
    """Get current user ID from request state."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return user_id

def get_current_company_id(request: Request) -> str:
    """Get current company ID from request state."""
    company_id = getattr(request.state, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=403, detail="Company context not found")
    return company_id

def get_lang_context(request: Request) -> LangContext:
    """Get language context from request."""
    # Get language from query param, header, or default to English
    lang = request.query_params.get("lang")
    if not lang:
        lang = request.headers.get("Accept-Language", "en")

    # Validate language
    if lang not in ["en", "ta"]:
        lang = "en"

    return LangContext.from_lang(Lang(lang))

async def get_db_session(
    trace_id: str = Depends(get_trace_id)
) -> AsyncSession:
    """Get database session with trace ID context."""
    async for session in get_async_session():
        # Add trace_id to session for logging
        session.info["trace_id"] = trace_id
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def require_company_access(
    company_id: str = Depends(get_current_company_id),
    _user_id: str = Depends(get_current_user_id)
) -> str:
    """Ensure user has access to the specified company."""
    # TODO: Implement proper company access check
    # For now, we'll assume the user has access
    return company_id

def get_pagination_params(
    page: int = 1,
    page_size: int = 20
) -> dict[str, int]:
    """Get and validate pagination parameters."""
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Page size must be between 1 and 100")

    offset = (page - 1) * page_size

    return {
        "page": page,
        "page_size": page_size,
        "offset": offset,
        "limit": page_size
    }
