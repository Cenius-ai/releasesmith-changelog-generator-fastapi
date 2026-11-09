"""Conventional-commit parsing for pasted changelog material.

The paste is split into commit *blocks* on blank lines: a subject line plus the
optional body and footer lines that belong to that same commit. Classifying
whole blocks (rather than raw lines) is what lets a ``BREAKING CHANGE:`` footer
attach to its commit instead of being counted as an unrelated line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# type(scope)!: description  -- scope and the bang are both optional.
SUBJECT_RE = re.compile(
    r"^(?P<type>[A-Za-z]+)\s*"
    r"(?:\(\s*(?P<scope>[^()]*?)\s*\))?\s*"
    r"(?P<bang>!)?\s*:\s*"
    r"(?P<description>.+?)\s*$"
)
BREAKING_FOOTER_RE = re.compile(r"^BREAKING[ -]CHANGE:\s*(?P<note>.*)$", re.IGNORECASE)

FEATURE_TYPES = frozenset({"feat", "feature"})
FIX_TYPES = frozenset({"fix"})


@dataclass(frozen=True)
class Commit:
    """One parsed conventional commit."""

    type: str
    scope: str | None
    description: str
    breaking: bool = False

    def to_dict(self) -> dict:
        return {"type": self.type, "scope": self.scope, "description": self.description}

    @classmethod
    def from_dict(cls, payload: dict) -> "Commit":
        return cls(
            type=str(payload.get("type") or ""),
            scope=(payload.get("scope") or None),
            description=str(payload.get("description") or ""),
        )


@dataclass
class ParseResult:
    """Grouped changelog material plus the count of unrelated subject lines."""

    breaking: list[Commit] = field(default_factory=list)
    features: list[Commit] = field(default_factory=list)
    fixes: list[Commit] = field(default_factory=list)
    skipped: int = 0

    @property
    def commit_count(self) -> int:
        """Number of pasted blocks that produced a changelog entry."""
        return len(self.breaking) + len(self.features) + len(self.fixes)

    @property
    def has_changes(self) -> bool:
        return bool(self.breaking or self.features or self.fixes)

    @property
    def is_breaking(self) -> bool:
        return bool(self.breaking)

    def to_dict(self) -> dict:
        return {
            "breaking": [commit.to_dict() for commit in self.breaking],
            "features": [commit.to_dict() for commit in self.features],
            "fixes": [commit.to_dict() for commit in self.fixes],
            "skipped_count": self.skipped,
            "commit_count": self.commit_count,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "ParseResult":
        payload = payload or {}
        return cls(
            breaking=[Commit.from_dict(item) for item in payload.get("breaking") or []],
            features=[Commit.from_dict(item) for item in payload.get("features") or []],
            fixes=[Commit.from_dict(item) for item in payload.get("fixes") or []],
            skipped=int(payload.get("skipped_count") or 0),
        )


def split_blocks(raw: str) -> list[list[str]]:
    """Split pasted text into commit blocks separated by one or more blank lines.

    A block that does not open with a conventional subject is treated as the body
    or footer of the commit above it; a leading block with no commit above it is
    kept as its own (and counted as skipped by :func:`parse_commits`).
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in (raw or "").splitlines():
        if line.strip():
            current.append(line.rstrip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)

    # Conventional commits put the body and the footers after a blank line, so a
    # block that does not start with a conventional subject is folded back into
    # the commit it follows instead of being read as a subject of its own. That
    # is what keeps a `BREAKING CHANGE:` footer attached to its commit.
    merged: list[list[str]] = []
    last_commit: int | None = None
    for block in blocks:
        if SUBJECT_RE.match(block[0].strip()):
            merged.append(list(block))
            last_commit = len(merged) - 1
        elif last_commit is not None:
            merged[last_commit].extend(block)
        else:
            merged.append(list(block))
    return merged


def parse_commits(raw: str) -> ParseResult:
    """Parse a pasted block of conventional-commit messages.

    ``feat`` lands in Features, ``fix`` in Fixes and anything flagged with a
    ``!`` or carrying a ``BREAKING CHANGE:`` footer lands in Breaking Changes.
    A subject line that matches none of those buckets is counted as skipped -
    body and footer lines never are.
    """
    result = ParseResult()

    for block in split_blocks(raw):
        subject = block[0].strip()
        match = SUBJECT_RE.match(subject)
        if match is None:
            result.skipped += 1
            continue

        commit_type = match.group("type").lower()
        scope = (match.group("scope") or "").strip() or None
        description = match.group("description").strip()
        breaking = bool(match.group("bang"))

        if not breaking:
            breaking = any(BREAKING_FOOTER_RE.match(line.strip()) for line in block[1:])

        commit = Commit(
            type=commit_type,
            scope=scope,
            description=description,
            breaking=breaking,
        )

        if breaking:
            result.breaking.append(commit)
        if commit_type in FEATURE_TYPES:
            result.features.append(commit)
        elif commit_type in FIX_TYPES:
            result.fixes.append(commit)
        elif not breaking:
            result.skipped += 1

    return result
