"""Resolve the signing secret used for the FastAPI session cookie."""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "aka_session"

_DEV_FALLBACK_SECRET = "dev-only-insecure-session-secret"


def get_session_secret() -> str:
    """Return the secret used by SessionMiddleware and cookie decoding.

    Must be identical in both places or Chainlit cannot trust aka_session.
    """
    if settings.SESSION_SECRET:
        return settings.SESSION_SECRET
    if settings.ENVIRONMENT == "production":
        raise RuntimeError(
            "SESSION_SECRET is not set. Refusing to start in production."
        )
    logger.warning(
        "SESSION_SECRET is not set; using an insecure development default. "
        "Add SESSION_SECRET to .env before treating sessions as real."
    )
    return _DEV_FALLBACK_SECRET
