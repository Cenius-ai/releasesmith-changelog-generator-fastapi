"""Sign-up, sign-in and sign-out routes."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password, set_flash, sign_in_session, sign_out_session, verify_password
from app.db import get_db
from app.dependencies import get_current_user, require_user, safe_next_path
from app.models import User
from app.web import render

router = APIRouter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
MIN_PASSWORD_LENGTH = 8
DEMO_EMAIL = "cenius@cenius.ai"


def _find_user_by_identifier(db: Session, identifier: str) -> User | None:
    """Resolve an email, or the local part of an email (so `cenius` works too)."""
    value = identifier.strip().lower()
    if not value:
        return None
    user = db.scalar(select(User).where(User.email == value))
    if user is not None or "@" in value:
        return user
    candidates = db.scalars(
        select(User).where(User.email.like(f"{value}@%")).order_by(User.id)
    ).all()
    return candidates[0] if candidates else None


def _signin_view(
    request: Request,
    next_path: str = "",
    *,
    db: Session,
    email: str = "",
    error: str | None = None,
    status_code: int = 200,
):
    """Render the sign-in card (shared by /login and /signin)."""
    user = get_current_user(request, db)
    if user is not None and error is None:
        return RedirectResponse("/dashboard", status_code=302)
    return render(
        request,
        "signin.html",
        None,
        email=email,
        next_path=safe_next_path(next_path),
        error=error,
        page_title="Sign in",
        status_code=status_code,
    )


@router.get("/login")
def login_page(
    request: Request,
    next: str = "",
    db: Session = Depends(get_db),
):
    """Canonical sign-in route."""
    return _signin_view(request, next, db=db)


@router.get("/signin")
def signin_page(
    request: Request,
    next: str = "",
    db: Session = Depends(get_db),
):
    """Alias kept for existing links; renders the same sign-in card."""
    return _signin_view(request, next, db=db)


@router.post("/auth/signin")
def signin_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    next: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _find_user_by_identifier(db, email)
    if user is None or not verify_password(password, user.password_hash, user.password_salt):
        # One non-enumerating message for both branches.
        return _signin_view(
            request,
            next,
            db=db,
            email=email.strip(),
            error="Email or password is incorrect.",
            status_code=400,
        )
    sign_in_session(request, user.id)
    set_flash(request, f"Signed in as {user.email}.")
    return RedirectResponse(safe_next_path(next), status_code=303)


@router.get("/signup")
def signup_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is not None:
        return RedirectResponse("/dashboard", status_code=302)
    return render(
        request,
        "signup.html",
        None,
        values={"display_name": "", "email": ""},
        errors={},
        page_title="Create account",
    )


@router.post("/auth/signup")
def signup_submit(
    request: Request,
    display_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
    db: Session = Depends(get_db),
):
    values = {"display_name": display_name.strip(), "email": email.strip()}
    errors: dict[str, str] = {}

    if not values["display_name"]:
        errors["display_name"] = "Tell us what to call you."
    if not EMAIL_RE.match(values["email"].lower()):
        errors["email"] = "Enter a valid email address."
    if len(password) < MIN_PASSWORD_LENGTH:
        errors["password"] = f"Use at least {MIN_PASSWORD_LENGTH} characters."
    if password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    if not errors:
        existing = db.scalar(select(User).where(User.email == values["email"].lower()))
        if existing is not None:
            errors["email"] = "An account with that email already exists."

    if errors:
        return render(
            request,
            "signup.html",
            None,
            values=values,
            errors=errors,
            page_title="Create account",
            status_code=400,
        )

    password_hash, password_salt = hash_password(password)
    user = User(
        email=values["email"].lower(),
        display_name=values["display_name"],
        password_hash=password_hash,
        password_salt=password_salt,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    sign_in_session(request, user.id)
    set_flash(request, f"Welcome to Releasesmith, {user.display_name}.")
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/auth/demo-signin")
def demo_signin(request: Request, db: Session = Depends(get_db)):
    """One-click shortcut for the seeded demo account (the credentials are public)."""
    user = _find_user_by_identifier(db, DEMO_EMAIL)
    if user is None:
        set_flash(request, "The demo account has not been seeded yet - run: python -m app.seed", "error")
        return RedirectResponse("/signin", status_code=303)
    sign_in_session(request, user.id)
    set_flash(request, f"Signed in as {user.email}.")
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/auth/signout")
def signout(request: Request, user: User = Depends(require_user)):
    sign_out_session(request)
    set_flash(request, "You have been signed out.", "info")
    return RedirectResponse("/signin", status_code=303)
