"""Password hashing and session helpers.

Passwords are stored as salted PBKDF2-SHA256 digests built with the Python
standard library only, so there is no native build step and no extra service.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 260_000
SALT_BYTES = 16
SESSION_USER_KEY = "user_id"
FLASH_KEY = "flash"


def hash_password(password: str, *, salt: str | None = None) -> tuple[str, str]:
    """Return ``(hash_hex, salt_hex)`` for a plaintext password."""
    if not password:
        raise ValueError("password must not be empty")
    salt_hex = salt or secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
    )
    return digest.hex(), salt_hex


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Constant-time verification of a plaintext password against a stored digest."""
    if not password or not password_hash or not salt:
        return False
    try:
        candidate, _ = hash_password(password, salt=salt)
    except ValueError:
        return False
    return hmac.compare_digest(candidate, password_hash)


def sign_in_session(request, user_id: int) -> None:
    """Rotate the session payload on login so a fixed session id cannot be reused."""
    request.session.clear()
    request.session[SESSION_USER_KEY] = user_id


def sign_out_session(request) -> None:
    request.session.clear()


def set_flash(request, message: str, kind: str = "success") -> None:
    request.session[FLASH_KEY] = {"message": message, "kind": kind}


def pop_flash(request) -> dict | None:
    """Read and clear the one-shot flash message (called from the base layout)."""
    if request is None:
        return None
    session = getattr(request, "session", None)
    if not session:
        return None
    return session.pop(FLASH_KEY, None)
