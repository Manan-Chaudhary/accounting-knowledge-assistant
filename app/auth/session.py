"""Helpers for the FastAPI signed session cookie."""

from __future__ import annotations

from fastapi import Request

from app.auth import SESSION_EMAIL_KEY, SESSION_ROLE_KEY, SESSION_USER_ID_KEY
from app.db.models import AppUser


def establish_session(request: Request, user: AppUser) -> None:
    """Replace any existing session identifier at successful sign-in (AU-45)."""
    request.session.clear()
    request.session[SESSION_USER_ID_KEY] = user.id
    request.session[SESSION_EMAIL_KEY] = user.email
    request.session[SESSION_ROLE_KEY] = user.role


def clear_session(request: Request) -> None:
    request.session.clear()


def session_user_payload(request: Request) -> dict | None:
    user_id = request.session.get(SESSION_USER_ID_KEY)
    email = request.session.get(SESSION_EMAIL_KEY)
    role = request.session.get(SESSION_ROLE_KEY)
    if user_id is None or not email or not role:
        return None
    return {"id": int(user_id), "email": str(email), "role": str(role)}
