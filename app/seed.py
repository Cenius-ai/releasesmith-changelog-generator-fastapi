"""Idempotent demo data: one primary demo account, one secondary, six releases.

Run with ``python -m app.seed`` (it creates tables first, then exits - it never
starts the HTTP server). The same routine runs on the normal boot path so a
fresh clone renders real content with no manual step.
"""

from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.db import SessionLocal, init_db
from app.models import Release, User, utcnow
from app.services.parser import ParseResult, parse_commits
from app.services.versioning import bump_level, suggest_version

PRIMARY_DEMO_EMAIL = "cenius@cenius.ai"
PRIMARY_DEMO_PASSWORD = "cenius"

DEMO_ACCOUNTS = [
    {
        "email": PRIMARY_DEMO_EMAIL,
        "display_name": "Cenius Maintainer",
        "password": PRIMARY_DEMO_PASSWORD,
    },
    {
        "email": "demo@releasesmith.dev",
        "display_name": "Demo Maintainer",
        "password": "demo1234",
    },
]

# previous_version drives the suggested version; days_ago staggers the history.
SEED_RELEASES = [
    {
        "name": "Composer polish",
        "previous_version": "2.1.0",
        "notes": "Two fixes from the beta feedback thread. Nothing to upgrade for.",
        "days_ago": 2,
        "commits": (
            "fix(templates): render empty sections with their own heading\n\n"
            "fix(auth): clear the password field after a failed sign-in\n\n"
            "chore: pin SQLAlchemy to 2.0.51\n"
        ),
    },
    {
        "name": "Filter the release history",
        "previous_version": "2.0.0",
        "notes": "Search the dashboard by release name or version. Thanks to everyone who asked for it.",
        "days_ago": 12,
        "commits": (
            "feat(dashboard): filter release history by name or version\n\n"
            "feat(composer): prefill every field when editing an existing release\n\n"
            "fix(versioning): reset minor and patch when a major bump lands\n\n"
            "docs: document the paste format in the README\n"
        ),
    },
    {
        "name": "Block-aware parser",
        "previous_version": "1.4.2",
        "notes": "Breaking: the parser now groups whole commit blocks, so a footer stays with its commit.",
        "days_ago": 27,
        "commits": (
            "feat(parser)!: split pasted commits into blocks before classifying\n\n"
            "Commit bodies and footers now travel with their subject line so a\n"
            "breaking footer is attributed to the right change.\n\n"
            "BREAKING CHANGE: parse_commits() returns grouped sections instead of a flat list\n\n"
            "fix(composer): keep the pasted text when a preview fails\n\n"
            "feat(export): add a Markdown download for saved releases\n\n"
            "chore: bump ruff to 0.6.2\n"
        ),
    },
    {
        "name": "Markdown export panel",
        "previous_version": "1.0.0",
        "notes": "Copy the rendered changelog straight into a GitHub release note.",
        "days_ago": 41,
        "commits": (
            "feat(export): render the changelog as Markdown from the stored groups\n\n"
            "feat(export): serve the release note as a .md download\n\n"
            "fix(releases): keep created_at when a release is edited\n"
        ),
    },
    {
        "name": "Edit saved releases",
        "previous_version": "0.9.4",
        "notes": "First release with the full lifecycle: save, reopen, edit, delete.",
        "days_ago": 58,
        "commits": (
            "refactor(api)!: rename the groups payload key to breaking/features/fixes\n\n"
            "BREAKING CHANGE: stored groups JSON uses the new section keys\n\n"
            "feat(releases): reopen a saved release in the composer\n\n"
            "fix(parser): tolerate stray blank lines between commits\n"
        ),
    },
    {
        "name": "First public release",
        "previous_version": "0.9.0",
        "notes": "The MVP: paste commits, preview the groups, save a changelog.",
        "days_ago": 76,
        "commits": (
            "feat(auth): add email and password sign-up with server sessions\n\n"
            "feat(parser): group feat, fix and breaking commits from a paste\n\n"
            "feat(versioning): suggest the next semantic version from the groups\n\n"
            "fix(layout): keep the composer usable on a phone\n"
        ),
    },
]

SECONDARY_ACCOUNT_RELEASE_COUNT = 3


def _ensure_user(db: Session, account: dict) -> tuple[User, bool]:
    email = account["email"].lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        return user, False
    password_hash, password_salt = hash_password(account["password"])
    user = User(
        email=email,
        display_name=account["display_name"],
        password_hash=password_hash,
        password_salt=password_salt,
    )
    db.add(user)
    db.flush()  # capture the generated id before any child rows reference it
    return user, True


def _release_exists(db: Session, user_id: int, version: str) -> bool:
    return (
        db.scalar(
            select(Release.id).where(Release.user_id == user_id, Release.version == version)
        )
        is not None
    )


def _build_release(user: User, spec: dict, groups: ParseResult, suggestion) -> Release:
    saved_at = utcnow() - timedelta(days=spec["days_ago"], hours=spec["days_ago"] % 7)
    return Release(
        user_id=user.id,
        name=spec["name"],
        version=suggestion.version,
        previous_version=suggestion.previous,
        bump_level=bump_level(groups),
        raw_commits=spec["commits"],
        groups_json=json.dumps(groups.to_dict()),
        notes=spec["notes"],
        created_at=saved_at,
        updated_at=saved_at,
    )


def seed_database(db: Session | None = None) -> str:
    """Create the demo accounts and releases if they are missing. Idempotent."""
    owns_session = db is None
    session = db or SessionLocal()
    created_users = 0
    created_releases = 0
    try:
        for index, account in enumerate(DEMO_ACCOUNTS):
            user, was_created = _ensure_user(session, account)
            created_users += int(was_created)

            specs = SEED_RELEASES if index == 0 else SEED_RELEASES[:SECONDARY_ACCOUNT_RELEASE_COUNT]
            for spec in specs:
                groups = parse_commits(spec["commits"])
                suggestion = suggest_version(spec["previous_version"], groups)
                if _release_exists(session, user.id, suggestion.version):
                    continue
                session.add(_build_release(user, spec, groups, suggestion))
                created_releases += 1

        session.commit()
    finally:
        if owns_session:
            session.close()

    return f"{created_users} user(s) and {created_releases} release(s) created"


def main() -> None:
    banner = "Releasesmith seed"
    print(f"{banner}: creating tables if needed ...")
    init_db()
    summary = seed_database()
    print(f"{banner}: done - {summary}.")
    print(
        "Demo login: "
        f"{PRIMARY_DEMO_EMAIL} / {PRIMARY_DEMO_PASSWORD}   "
        "(also demo@releasesmith.dev / demo1234)"
    )


if __name__ == "__main__":
    main()
