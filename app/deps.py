"""Request-scoped dependencies: session user lookup and the signed-out redirect."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import StaffUser

SESSION_USER_KEY = "staff_user_id"


class SignInRequired(Exception):
    """Raised by a guarded route; the handler redirects to the sign-in page."""

    def __init__(self, next_path: str = "/") -> None:
        self.next_path = next_path
        super().__init__("sign in required")


def session_user_id(request: Request) -> int | None:
    raw = request.session.get(SESSION_USER_KEY)
    if isinstance(raw, int):
        return raw
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> StaffUser | None:
    user_id = session_user_id(request)
    if user_id is None:
        return None
    return db.get(StaffUser, user_id)


def require_staff(request: Request, user: StaffUser | None = Depends(get_current_user)) -> StaffUser:
    """Every workshop page depends on this: signed out means redirect, never data."""
    if user is None:
        request.session.pop(SESSION_USER_KEY, None)
        raise SignInRequired(next_path=request.url.path)
    return user


def safe_next_path(raw: str | None) -> str:
    """Only allow same-site, relative redirect targets."""
    candidate = (raw or "").strip()
    if candidate.startswith("/") and not candidate.startswith("//") and "\\" not in candidate:
        return candidate
    return "/"
