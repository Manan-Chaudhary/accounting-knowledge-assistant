"""Map an established FastAPI session to a Chainlit user (AU-84)."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

import chainlit as cl

from app.auth.cookie import session_payload_from_cookie_header
from app.db.database import SessionLocal
from app.db.models import AppUser

logger = logging.getLogger(__name__)


def user_from_request_headers(headers: Mapping[str, Any]) -> Optional[cl.User]:
    """Trust identity already established by FastAPI — do not check passwords here."""
    cookie_header = headers.get("cookie") or headers.get("Cookie")
    if cookie_header is not None and not isinstance(cookie_header, str):
        cookie_header = str(cookie_header)

    payload = session_payload_from_cookie_header(cookie_header)
    if payload is None:
        return None

    db = SessionLocal()
    try:
        user = db.get(AppUser, payload["id"])
        if user is None or not user.is_active:
            return None
        # Session email must still match the live account record.
        if user.email.lower() != str(payload["email"]).lower():
            return None
        return cl.User(
            identifier=user.email,
            metadata={
                "role": user.role,
                "user_id": user.id,
                "provider": "fastapi_session",
            },
        )
    except Exception:
        logger.exception("chainlit_header_auth_lookup_failed")
        return None
    finally:
        db.close()
