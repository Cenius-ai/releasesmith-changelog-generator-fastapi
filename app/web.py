"""Shared template plumbing: Jinja environment, formatters and page context."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.auth import pop_flash
from app.config import settings
from app.models import Release
from app.services.markdown import render_markdown
from app.services.parser import ParseResult

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["pop_flash"] = pop_flash
templates.env.globals["product_name"] = settings.app_name


def human_date(value: datetime | None) -> str:
    if not value:
        return "-"
    return value.strftime("%d %b %Y")


def human_datetime(value: datetime | None) -> str:
    if not value:
        return "-"
    return value.strftime("%d %b %Y, %H:%M UTC")


def relative_time(value: datetime | None) -> str:
    """Relative label for recent timestamps, absolute date once older than a week."""
    if not value:
        return "-"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    delta = now - value
    seconds = delta.total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    if seconds < 86_400:
        return f"{int(seconds // 3600)} h ago"
    if seconds < 7 * 86_400:
        return f"{int(seconds // 86_400)} days ago"
    return human_date(value)


def pluralise(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {word}"


templates.env.filters["human_date"] = human_date
templates.env.filters["human_datetime"] = human_datetime
templates.env.filters["timeago"] = relative_time
templates.env.filters["pluralise"] = pluralise


def render(
    request: Request,
    template_name: str,
    user=None,
    *,
    status_code: int = 200,
    **context,
):
    """Render a page with the shared context every layout expects."""
    payload = {
        "current_user": user,
        "product_name": settings.app_name,
        **context,
    }
    return templates.TemplateResponse(request, template_name, payload, status_code=status_code)


def release_groups(release: Release) -> ParseResult:
    """Deserialize the stored groups defensively - bad JSON degrades, never 500s."""
    try:
        payload = json.loads(release.groups_json or "{}")
    except (TypeError, ValueError):
        return ParseResult()
    if not isinstance(payload, dict):
        return ParseResult()
    return ParseResult.from_dict(payload)


def release_markdown(release: Release) -> str:
    return render_markdown(
        version=release.version,
        previous_version=release.previous_version,
        name=release.name,
        notes=release.notes,
        groups=release_groups(release),
    )
