"""Auth dependencies for protected API routes."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import SESSION_USER_ID_KEY
from app.db.database import get_db
from app.db.models import AppUser


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> AppUser:
    user_id = request.session.get(SESSION_USER_ID_KEY)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user = db.get(AppUser, int(user_id))
    if user is None or not user.is_active:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user
