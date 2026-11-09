"""The changelog composer: paste commits, preview the grouped result, then save."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_owned_release, require_user
from app.models import Release, User
from app.services.parser import ParseResult, parse_commits
from app.services.versioning import (
    DEFAULT_PREVIOUS_VERSION,
    VersionSuggestion,
    suggest_version,
)
from app.web import render

router = APIRouter()

EXAMPLE_COMMITS = """feat(export): add Markdown download for a saved release
fix(composer): keep the pasted block when a preview fails
chore: bump ruff to 0.6.2

refactor(parser)!: split commits into blocks before classifying them

BREAKING CHANGE: parse_commits now returns grouped sections instead of a flat list
"""


def compose_page(
    request: Request,
    user: User,
    *,
    template: str,
    status_code: int = 200,
    release: Release | None = None,
    commits: str = "",
    previous_version: str = DEFAULT_PREVIOUS_VERSION,
    name: str = "",
    notes: str = "",
    version: str = "",
    groups: ParseResult | None = None,
    suggestion: VersionSuggestion | None = None,
    errors: dict[str, str] | None = None,
):
    """Render the composer in create mode, or in edit mode when ``release`` is set."""
    return render(
        request,
        template,
        user,
        status_code=status_code,
        release=release,
        mode="edit" if release else "create",
        commits=commits,
        previous_version=previous_version,
        name=name,
        notes=notes,
        version=version,
        groups=groups,
        suggestion=suggestion,
        errors=errors or {},
        previewed=groups is not None,
        page_title=f"Edit release {release.version}" if release else "New release",
    )


@router.get("/composer")
def composer_page(
    request: Request,
    example: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    commits = EXAMPLE_COMMITS if example else ""
    groups = parse_commits(commits) if commits else None
    suggestion = suggest_version(DEFAULT_PREVIOUS_VERSION, groups) if groups else None
    return compose_page(
        request,
        user,
        template="composer.html",
        commits=commits,
        previous_version=DEFAULT_PREVIOUS_VERSION,
        version=suggestion.version if suggestion else "",
        groups=groups,
        suggestion=suggestion,
    )


@router.get("/releases/new")
def new_release_page(
    request: Request,
    example: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """The composer mounted at the release resource path (/composer renders the same page)."""
    return composer_page(request, example=example, db=db, user=user)


@router.post("/composer/preview")
def preview(
    request: Request,
    commits: str = Form(""),
    previous_version: str = Form(DEFAULT_PREVIOUS_VERSION),
    name: str = Form(""),
    notes: str = Form(""),
    version: str = Form(""),
    release_id: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Parse the pasted block and re-render the composer - nothing is persisted."""
    release = None
    if release_id.strip().isdigit():
        release = get_owned_release(int(release_id), user, db)

    errors: dict[str, str] = {}
    groups: ParseResult | None = None
    suggestion: VersionSuggestion | None = None

    if not commits.strip():
        errors["commits"] = "Paste at least one commit."
    else:
        groups = parse_commits(commits)
        try:
            suggestion = suggest_version(previous_version, groups)
        except ValueError:
            errors["previous_version"] = "Previous version must look like 1.4.2."

    return compose_page(
        request,
        user,
        template="release_edit.html" if release else "composer.html",
        status_code=400 if errors else 200,
        release=release,
        commits=commits,
        previous_version=previous_version.strip() or DEFAULT_PREVIOUS_VERSION,
        name=name,
        notes=notes,
        version=version.strip() or (suggestion.version if suggestion else ""),
        groups=groups,
        suggestion=suggestion,
        errors=errors,
    )
