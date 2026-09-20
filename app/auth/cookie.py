"""Decode the FastAPI-owned aka_session cookie (Starlette SessionMiddleware format)."""

from __future__ import annotations

import json
import logging
from base64 import b64decode
from http.cookies import SimpleCookie

from itsdangerous import BadSignature, TimestampSigner

from app.auth import SESSION_EMAIL_KEY, SESSION_ROLE_KEY, SESSION_USER_ID_KEY
from app.auth.secrets import SESSION_COOKIE_NAME, get_session_secret
from app.config import settings

logger = logging.getLogger(__name__)


def extract_cookie_value(cookie_header: str | None, name: str) -> str | None:
    if not cookie_header:
        return None
    jar = SimpleCookie()
    try:
        jar.load(cookie_header)
    except Exception:
        return None
    morsel = jar.get(name)
    return morsel.value if morsel else None


def decode_session_cookie(cookie_value: str | None) -> dict | None:
    """Unsign and parse a Starlette SessionMiddleware cookie value."""
    if not cookie_value or cookie_value == "null":
        return None

    signer = TimestampSigner(str(get_session_secret()))
    try:
        raw = signer.unsign(
            cookie_value.encode("utf-8"),
            max_age=settings.SESSION_MAX_AGE_SECONDS,
        )
        data = json.loads(b64decode(raw))
    except (BadSignature, ValueError, json.JSONDecodeError):
        logger.info("aka_session_decode_failed")
        return None

    if not isinstance(data, dict):
        return None
    return data


def session_payload_from_cookie_header(cookie_header: str | None) -> dict | None:
    """Return {id, email, role} from a Cookie header, or None."""
    value = extract_cookie_value(cookie_header, SESSION_COOKIE_NAME)
    data = decode_session_cookie(value)
    if not data:
        return None

    user_id = data.get(SESSION_USER_ID_KEY)
    email = data.get(SESSION_EMAIL_KEY)
    role = data.get(SESSION_ROLE_KEY)
    if user_id is None or not email or not role:
        return None
    try:
        return {"id": int(user_id), "email": str(email), "role": str(role)}
    except (TypeError, ValueError):
        return None
