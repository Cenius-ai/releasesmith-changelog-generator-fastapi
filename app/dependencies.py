"""Request-scoped dependencies: the signed-in user and ownership gates."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import SESSION_USER_KEY
from app.db import get_db
from app.models import Release, User


class AuthRequired(Exception):
    """Raised by gated page routes; handled with a redirect to /signin."""

    def __init__(self, next_path: str | None = None) -> None:
        self.next_path = next_path
        super().__init__("authentication required")


class PageNotFound(Exception):
    """Raised when a page (or a record) does not exist for this user."""


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Return the signed-in user, or None for an anonymous visitor."""
    user_id = request.session.get(SESSION_USER_KEY) if request.session else None
    if not user_id:
        return None
    return db.get(User, user_id)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Return the signed-in user or bounce the visitor to the sign-in page."""
    user = get_current_user(request, db)
    if user is None:
        path = request.url.path or "/"
        raise AuthRequired(path)
    return user


def get_owned_release(release_id: int, user: User, db: Session) -> Release:
    """Load a release scoped to its owner; a foreign id is indistinguishable from a
    missing one so record ids cannot be enumerated across accounts."""
    release = db.scalar(
        select(Release).where(Release.id == release_id, Release.user_id == user.id)
    )
    if release is None:
        raise PageNotFound(f"release {release_id}")
    return release


def safe_next_path(candidate: str | None) -> str:
    """Only allow same-origin relative paths as a post-login destination."""
    if not candidate or not candidate.startswith("/") or candidate.startswith("//"):
        return "/dashboard"
    return quote(candidate, safe="/?=&")
