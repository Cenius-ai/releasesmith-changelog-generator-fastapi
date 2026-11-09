"""Root-module entrypoint.

The application lives in ``app/main.py`` (``uvicorn app.main:app``). This alias
exists so ``uvicorn main:app`` works too, which is the conventional command for
single-module FastAPI projects.
"""

from app.main import app  # noqa: F401

__all__ = ["app"]
