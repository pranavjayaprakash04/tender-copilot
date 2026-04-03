from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from app.dependencies import get_current_company_id, get_current_user_id


@dataclass
class CurrentUser:
    user_id: str
    company_id: str


def get_current_user(
    user_id: str = Depends(get_current_user_id),
    company_id: str = Depends(get_current_company_id),
) -> CurrentUser:
    """Return a combined user+company context object."""
    return CurrentUser(user_id=user_id, company_id=company_id)
