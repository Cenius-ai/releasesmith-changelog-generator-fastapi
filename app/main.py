"""Releasesmith - FastAPI application.

Run with:  uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.datastructures import MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.auth import set_flash
from app.config import settings
from app.db import SessionLocal, get_db, init_db
from app.dependencies import AuthRequired, PageNotFound, get_current_user
from app.routers import auth as auth_routes
from app.routers import composer as composer_routes
from app.routers import dashboard as dashboard_routes
from app.routers import releases as release_routes
from app.web import STATIC_DIR, render

logger = logging.getLogger("releasesmith")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create the schema and make sure the demo data exists on every boot."""
    init_db()
    try:
        from app.seed import seed_database

        summary = seed_database()
        logger.info("seed check complete: %s", summary)
    except Exception:  # noqa: BLE001 - boot must survive a seeding problem, loudly
        logger.exception("demo seed failed; serving with whatever data exists")
    logger.info("Releasesmith ready - listening on 0.0.0.0:%s", os.environ.get("PORT", 8000))
    yield


app = FastAPI(
    title="Releasesmith Changelog Generator",
    description="Turn conventional-commit messages into a grouped changelog and a semantic version bump.",
    version="1.0.0",
    lifespan=lifespan,
)


class SecurityHeadersMiddleware:
    """Security headers for every response (the app serves its own HTML)."""

    CONTENT_SECURITY_POLICY = "; ".join(
        [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self'",
            "form-action 'self'",
            "base-uri 'self'",
            "frame-ancestors 'none'",
            "object-src 'none'",
        ]
    )

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
                headers.setdefault("Content-Security-Policy", self.CONTENT_SECURITY_POLICY)
                headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
            await send(message)

        await self.app(scope, receive, send_with_headers)


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=settings.session_max_age,
    same_site="lax",
    https_only=False,  # the app is served over plain HTTP locally
)
app.add_middleware(SecurityHeadersMiddleware)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(composer_routes.router)
app.include_router(release_routes.router)


@app.get("/", include_in_schema=False)
def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return RedirectResponse("/dashboard" if user else "/signin", status_code=302)


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


def _not_found(request: Request) -> object:
    session = SessionLocal()
    try:
        user = get_current_user(request, session)
    finally:
        session.close()
    return render(request, "404.html", user, page_title="Page not found", status_code=404)


@app.exception_handler(PageNotFound)
async def handle_page_not_found(request: Request, _exc: PageNotFound):
    return _not_found(request)


@app.exception_handler(AuthRequired)
async def handle_auth_required(request: Request, exc: AuthRequired):
    set_flash(request, "Please sign in to continue.", "info")
    target = exc.next_path or "/dashboard"
    url = "/signin"
    if target not in ("/", "/dashboard", "/signin"):
        url = f"/signin?next={quote(target, safe='/?=&')}"
    return RedirectResponse(url, status_code=302)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return _not_found(request)
    logger.warning("HTTP %s on %s", exc.status_code, request.url.path)
    return JSONResponse({"detail": exc.detail or "request failed"}, status_code=exc.status_code)
