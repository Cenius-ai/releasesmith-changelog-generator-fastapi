"""Markdown rendering for a saved release (one renderer feeds preview and export)."""

from __future__ import annotations

from app.services.parser import Commit, ParseResult

SECTION_BREAKING = "Breaking Changes"
SECTION_FEATURES = "Features"
SECTION_FIXES = "Fixes"


def _bullet(commit: Commit) -> str:
    if commit.scope:
        return f"- {commit.description} ({commit.scope})"
    return f"- {commit.description}"


def _section(title: str, commits: list[Commit]) -> list[str]:
    if not commits:
        return []
    return [f"### {title}", ""] + [_bullet(commit) for commit in commits] + [""]


def render_markdown(
    *,
    version: str,
    groups: ParseResult,
    previous_version: str | None = None,
    name: str | None = None,
    notes: str | None = None,
) -> str:
    """Render the changelog as GitHub-flavoured Markdown."""
    lines: list[str] = [f"## v{version}", ""]

    if previous_version:
        lines += [f"_Previous release: v{previous_version}_", ""]

    if name and name.strip():
        lines += [f"**{name.strip()}**", ""]

    if notes and notes.strip():
        lines += [notes.strip(), ""]

    if not groups.has_changes:
        lines += ["_No conventional-commit changes in this release._", ""]
    else:
        lines += _section(SECTION_BREAKING, groups.breaking)
        lines += _section(SECTION_FEATURES, groups.features)
        lines += _section(SECTION_FIXES, groups.fixes)

    return "\n".join(lines).rstrip() + "\n"
