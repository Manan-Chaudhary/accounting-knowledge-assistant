import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.session import session_user_payload
from app.db.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/threads")
def list_user_threads(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Fetch recent conversation threads for the current user."""
    payload = session_user_payload(request)
    if not payload:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication required."},
        )

    user_email = payload.get("email")
    user_sub = str(payload.get("sub")) if payload.get("sub") else None

    query = text("""
        SELECT 
            t.id, 
            COALESCE(
                NULLIF(TRIM(t.name), ''), 
                (
                    SELECT COALESCE(NULLIF(TRIM(s.output), ''), NULLIF(TRIM(s.input), ''))
                    FROM steps s 
                    WHERE s."threadId" = t.id 
                      AND (s.type = 'user_message' OR s.name = 'user')
                    ORDER BY s."createdAt" ASC 
                    LIMIT 1
                ),
                'New Conversation'
            ) AS name,
            t."createdAt"
        FROM threads t
        WHERE (t."userIdentifier" = :user_email OR t."userIdentifier" = :user_sub)
        ORDER BY t."createdAt" DESC
        LIMIT 20
    """)

    try:
        results = db.execute(query, {"user_email": user_email, "user_sub": user_sub}).fetchall()
        threads: List[Dict[str, Any]] = []
        for row in results:
            created_at_val = row.createdAt
            created_at_str = (
                created_at_val.isoformat()
                if hasattr(created_at_val, "isoformat")
                else (str(created_at_val) if created_at_val else None)
            )

            title = str(row.name or "New Conversation").strip()
            if len(title) > 35:
                title = title[:35] + "..."

            threads.append({
                "id": str(row.id),
                "name": title,
                "createdAt": created_at_str,
            })
        return JSONResponse(content=threads)
    except Exception as e:
        logger.exception("Failed to query user threads: %s", e)
        return JSONResponse(content=[])


@router.get("/threads/{thread_id}/messages")
def get_thread_messages(
    thread_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Fetch all historical conversation steps for a specific thread."""
    payload = session_user_payload(request)
    if not payload:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Unauthorized"})

    user_email = payload.get("email")
    user_sub = str(payload.get("sub")) if payload.get("sub") else None

    # Verify ownership
    verify_query = text("""
        SELECT id FROM threads
        WHERE id = :thread_id AND ("userIdentifier" = :user_email OR "userIdentifier" = :user_sub)
    """)
    if not db.execute(verify_query, {"thread_id": thread_id, "user_email": user_email, "user_sub": user_sub}).fetchone():
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Thread not found."})

    # Retrieve all user & assistant messages for this thread
    steps_query = text("""
        SELECT id, name, type, output, input, "createdAt"
        FROM steps
        WHERE "threadId" = :thread_id
        ORDER BY "createdAt" ASC
    """)
    results = db.execute(steps_query, {"thread_id": thread_id}).fetchall()

    messages: List[Dict[str, Any]] = []
    for row in results:
        content = (row.output or row.input or "").strip()
        if not content:
            continue

        is_user = row.type in ("user_message", "user") or row.name == "user"
        is_assistant = (
            row.type in ("assistant_message", "assistant")
            or "assistant" in (row.name or "").lower()
            or "alfa" in (row.name or "").lower()
        )
        if not (is_user or is_assistant):
            continue

        messages.append({
            "id": str(row.id),
            "type": "user_message" if is_user else "assistant_message",
            "name": "user" if is_user else "Alfa Focus Assistant",
            "output": content,
            "createdAt": str(row.createdAt) if row.createdAt else None,
        })

    return JSONResponse(content=messages)


@router.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Delete thread and associated steps."""
    payload = session_user_payload(request)
    if not payload:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Unauthorized"})

    user_email = payload.get("email")
    user_sub = str(payload.get("sub")) if payload.get("sub") else None

    try:
        db.execute(text('DELETE FROM steps WHERE "threadId" = :thread_id'), {"thread_id": thread_id})
        try:
            db.execute(text('DELETE FROM elements WHERE "threadId" = :thread_id'), {"thread_id": thread_id})
        except Exception:
            pass
        db.execute(
            text('DELETE FROM threads WHERE id = :thread_id AND ("userIdentifier" = :user_email OR "userIdentifier" = :user_sub)'),
            {"thread_id": thread_id, "user_email": user_email, "user_sub": user_sub}
        )
        db.commit()
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        db.rollback()
        logger.exception("Failed to delete thread: %s", e)
        return JSONResponse(status_code=500, content={"detail": "Failed to delete"})