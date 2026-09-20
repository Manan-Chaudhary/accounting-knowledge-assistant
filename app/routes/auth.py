"""Login / logout / me — FastAPI owns credential checks and the session."""

from __future__ import annotations

import logging
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import EMAIL_MAX_LENGTH, PASSWORD_MAX_LENGTH
from app.auth.deps import get_current_user
from app.auth.logout_cookies import clear_chainlit_auth_cookies
from app.auth.passwords import verify_password
from app.auth.session import clear_session, establish_session, session_user_payload
from app.db.database import get_db
from app.db.models import AppUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Generic failure copy — never reveal which field was wrong (AU-32, AU-33).
INVALID_CREDENTIALS = (
    "The credentials were not recognised. Check your email and password and try again."
)
ACCOUNT_INACTIVE = (
    "This account is not active. Contact your Alfa Focus administrator."
)
SIGN_IN_UNAVAILABLE = "Sign-in is temporarily unavailable. Please try again shortly."


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=EMAIL_MAX_LENGTH)
    # Password is never trimmed or case-folded (AU-19).
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserResponse(BaseModel):
    id: int
    email: str
    role: str


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_login_fields(email: str, password: str) -> None:
    """Server-side field checks before any credential lookup (AU-17–AU-22)."""
    normalized = _normalize_email(email)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email is required.",
        )
    if not _EMAIL_RE.match(normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter a valid email address.",
        )
    if not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password is required.",
        )


@router.post("/login", response_model=UserResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> UserResponse:
    _validate_login_fields(body.email, body.password)
    email = _normalize_email(body.email)
    # Constant-ish delay so unknown emails do not return faster (AU-38, soft).
    started = time.perf_counter()

    try:
        user = db.query(AppUser).filter(AppUser.email == email).one_or_none()
    except Exception:
        logger.exception("login_db_unavailable email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SIGN_IN_UNAVAILABLE,
        ) from None

    password_ok = verify_password(body.password, user.password_hash if user else None)

    if user is None or not password_ok:
        logger.info("login_failed email=%s reason=credentials", email)
        _pad_response_time(started)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        )

    if not user.is_active:
        logger.info("login_failed email=%s reason=inactive", email)
        _pad_response_time(started)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ACCOUNT_INACTIVE,
        )

    establish_session(request, user)
    logger.info("login_success user_id=%s email=%s role=%s", user.id, user.email, user.role)
    _pad_response_time(started)
    return UserResponse(id=user.id, email=user.email, role=user.role)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> None:
    clear_session(request)
    # End Chainlit JWT cookies issued after header auth (AU-87).
    clear_chainlit_auth_cookies(request, response)


@router.get("/me", response_model=UserResponse)
def me(
    request: Request,
    user: AppUser = Depends(get_current_user),
) -> UserResponse:
    # Prefer live DB values over stale session role (AU-40).
    payload = session_user_payload(request)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return UserResponse(id=user.id, email=user.email, role=user.role)


def _pad_response_time(started: float, minimum_seconds: float = 0.25) -> None:
    elapsed = time.perf_counter() - started
    remaining = minimum_seconds - elapsed
    if remaining > 0:
        time.sleep(remaining)
