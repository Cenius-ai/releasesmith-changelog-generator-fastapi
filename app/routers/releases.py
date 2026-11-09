"""Release CRUD: create, read, update, delete and Markdown export."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import set_flash
from app.db import get_db
from app.dependencies import get_owned_release, require_user
from app.models import Release, User, utcnow
from app.routers.composer import compose_page
from app.services.parser import ParseResult, parse_commits
from app.services.versioning import (
    DEFAULT_PREVIOUS_VERSION,
    VersionSuggestion,
    bump_level,
    is_valid_version,
    normalise_version,
    suggest_version,
)
from app.web import release_groups, release_markdown, render

router = APIRouter()


def _validate(
    commits: str, previous_version: str, version: str
) -> tuple[ParseResult | None, VersionSuggestion | None, str, str, dict[str, str]]:
    """Parse + validate the composer payload, returning values needed to re-render."""
    errors: dict[str, str] = {}
    groups: ParseResult | None = None
    suggestion: VersionSuggestion | None = None
    previous = normalise_version(previous_version) or DEFAULT_PREVIOUS_VERSION

    if not commits.strip():
        errors["commits"] = "Paste at least one commit."
    else:
        groups = parse_commits(commits)
        try:
            suggestion = suggest_version(previous, groups)
        except ValueError:
            errors["previous_version"] = "Previous version must look like 1.4.2."

    final_version = normalise_version(version) or (suggestion.version if suggestion else "")
    if final_version and not is_valid_version(final_version):
        errors["version"] = "Version must look like 1.4.2."

    return groups, suggestion, final_version, previous, errors


@router.post("/releases")
def create_release(
    request: Request,
    name: str = Form(""),
    notes: str = Form(""),
    version: str = Form(""),
    previous_version: str = Form(DEFAULT_PREVIOUS_VERSION),
    commits: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    groups, suggestion, final_version, previous, errors = _validate(
        commits, previous_version, version
    )

    if errors:
        return compose_page(
            request,
            user,
            template="composer.html",
            status_code=400,
            commits=commits,
            previous_version=previous,
            name=name,
            notes=notes,
            version=final_version,
            groups=groups,
            suggestion=suggestion,
            errors=errors,
        )

    release = Release(
        user_id=user.id,
        name=name.strip() or f"Release v{final_version}",
        version=final_version,
        previous_version=previous,
        bump_level=bump_level(groups),
        raw_commits=commits,
        groups_json=json.dumps(groups.to_dict()),
        notes=notes.strip() or None,
    )
    db.add(release)
    db.commit()
    db.refresh(release)

    set_flash(request, f"Saved release v{release.version}.")
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/releases/{release_id}")
def release_detail(
    release_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    release = get_owned_release(release_id, user, db)
    return render(
        request,
        "release_detail.html",
        user,
        page_title=f"v{release.version} - {release.name}",
        release=release,
        groups=release_groups(release),
        markdown=release_markdown(release),
    )


@router.get("/releases/{release_id}/edit")
def edit_release(
    release_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    release = get_owned_release(release_id, user, db)
    groups = release_groups(release)
    try:
        suggestion = suggest_version(release.previous_version, groups)
    except ValueError:
        suggestion = None

    return compose_page(
        request,
        user,
        template="release_edit.html",
        release=release,
        commits=release.raw_commits,
        previous_version=release.previous_version,
        name=release.name,
        notes=release.notes or "",
        version=release.version,
        groups=groups,
        suggestion=suggestion,
    )


@router.post("/releases/{release_id}")
def update_release(
    release_id: int,
    request: Request,
    name: str = Form(""),
    notes: str = Form(""),
    version: str = Form(""),
    previous_version: str = Form(DEFAULT_PREVIOUS_VERSION),
    commits: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    release = get_owned_release(release_id, user, db)
    groups, suggestion, final_version, previous, errors = _validate(
        commits, previous_version, version
    )

    if errors:
        return compose_page(
            request,
            user,
            template="release_edit.html",
            status_code=400,
            release=release,
            commits=commits,
            previous_version=previous,
            name=name,
            notes=notes,
            version=final_version,
            groups=groups,
            suggestion=suggestion,
            errors=errors,
        )

    release.name = name.strip() or release.name
    release.notes = notes.strip() or None
    release.version = final_version
    release.previous_version = previous
    release.bump_level = bump_level(groups)
    release.raw_commits = commits
    release.groups_json = json.dumps(groups.to_dict())
    release.updated_at = utcnow()  # created_at is deliberately untouched
    db.commit()

    set_flash(request, f"Updated release v{release.version}.")
    return RedirectResponse(f"/releases/{release.id}", status_code=303)


@router.post("/releases/{release_id}/delete")
def delete_release(
    release_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    release = get_owned_release(release_id, user, db)
    label = f"v{release.version}"
    db.delete(release)
    db.commit()

    set_flash(request, f"Deleted release {label}.", "info")
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/releases/{release_id}/export.md")
def export_release_markdown(
    release_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    release = get_owned_release(release_id, user, db)
    markdown = release_markdown(release)
    filename = f"releasesmith-v{release.version}.md"
    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
