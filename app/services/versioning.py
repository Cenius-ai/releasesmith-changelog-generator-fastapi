"""Semantic version bumping: breaking -> major, feat -> minor, fix-only -> patch."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.parser import ParseResult

SEMVER_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")

DEFAULT_PREVIOUS_VERSION = "1.0.0"
LEVEL_MAJOR = "major"
LEVEL_MINOR = "minor"
LEVEL_PATCH = "patch"


@dataclass(frozen=True)
class VersionSuggestion:
    previous: str
    version: str
    level: str

    @property
    def label(self) -> str:
        return f"{self.level} bump"


def normalise_version(value: str | None) -> str:
    """Tolerate a leading ``v`` and surrounding whitespace."""
    return (value or "").strip().lstrip("vV")


def is_valid_version(value: str | None) -> bool:
    return bool(SEMVER_RE.match(normalise_version(value)))


def bump_level(groups: ParseResult) -> str:
    """The bump implied by the parsed groups."""
    if groups.breaking:
        return LEVEL_MAJOR
    if groups.features:
        return LEVEL_MINOR
    return LEVEL_PATCH


def suggest_version(previous: str | None, groups: ParseResult) -> VersionSuggestion:
    """Compute the next version from the previous one and the parsed groups.

    Raises ``ValueError`` when ``previous`` is not a ``major.minor.patch`` version.
    """
    normalised = normalise_version(previous) or DEFAULT_PREVIOUS_VERSION
    match = SEMVER_RE.match(normalised)
    if match is None:
        raise ValueError(f"'{previous}' is not a semantic version (expected major.minor.patch)")

    major, minor, patch = (int(match.group(key)) for key in ("major", "minor", "patch"))
    level = bump_level(groups)

    if level == LEVEL_MAJOR:
        major, minor, patch = major + 1, 0, 0
    elif level == LEVEL_MINOR:
        minor, patch = minor + 1, 0
    else:
        patch += 1

    return VersionSuggestion(
        previous=normalised,
        version=f"{major}.{minor}.{patch}",
        level=level,
    )
