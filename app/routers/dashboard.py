"""Release history dashboard with an optional name/version filter."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_user
from app.models import Release, User
from app.web import release_groups, render

router = APIRouter()


def _stats(releases: list[Release]) -> dict:
    """Group counts across every release the user owns (independent of the filter)."""
    features = fixes = breaking = 0
    for release in releases:
        groups = release_groups(release)
        features += len(groups.features)
        fixes += len(groups.fixes)
        breaking += len(groups.breaking)
    return {
        "releases": len(releases),
        "features": features,
        "fixes": fixes,
        "breaking": breaking,
    }


def _matches(release: Release, term: str) -> bool:
    needle = term.lower()
    return needle in release.name.lower() or needle in release.version.lower()


@router.get("/dashboard")
def dashboard(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    term = q.strip()
    all_releases = list(
        db.scalars(
            select(Release)
            .where(Release.user_id == user.id)
            .order_by(Release.created_at.desc(), Release.id.desc())
        )
    )
    releases = [release for release in all_releases if _matches(release, term)] if term else all_releases
    rows = [{"release": release, "groups": release_groups(release)} for release in releases]

    return render(
        request,
        "dashboard.html",
        user,
        page_title="Release history",
        rows=rows,
        total_releases=len(all_releases),
        stats=_stats(all_releases),
        query=term,
    )
