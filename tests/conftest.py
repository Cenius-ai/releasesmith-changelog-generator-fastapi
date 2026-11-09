"""Test fixtures: an isolated SQLite file and clients for the real ASGI app."""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Point the app at a throwaway database *before* importing it.
_TMP_DIR = pathlib.Path(tempfile.mkdtemp(prefix="releasesmith-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR / 'test.db'}"
os.environ["SECRET_KEY"] = "pytest-only-cookie-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

DEMO_EMAIL = "cenius@cenius.ai"
DEMO_PASSWORD = "cenius"

SAMPLE_COMMITS = (
    "feat(api): add token refresh\n\n"
    "fix(ui): stop double submit\n\n"
    "chore: bump deps\n\n"
    "refactor(db)!: swap driver\n\n"
    "BREAKING CHANGE: old DSNs no longer parse\n"
)


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_client(client):
    response = client.post(
        "/auth/signin",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    assert response.headers["location"] == "/dashboard"
    return client


@pytest.fixture()
def second_user_client():
    """A second, independent account used for cross-account access checks."""
    with TestClient(app) as other:
        email = "reviewer+%s@example.com" % os.urandom(4).hex()
        response = other.post(
            "/auth/signup",
            data={
                "display_name": "Second Reviewer",
                "email": email,
                "password": "***REDACTED-SECRET***",
                "confirm_password": "***REDACTED-SECRET***",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text
        other.email = email
        yield other
