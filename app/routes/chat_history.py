import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.session import session_user_payload
from app.db.database import SessionLocal, get_db
from app.rag.generator import generate_response, generate_response_stream
from app.rag.grounding import evaluate_grounding_gate, verify_and_clean_citations
from app.rag.retriever import format_retrieved_context, retrieve, retrieve_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class RenameThreadRequest(BaseModel):
    name: str


class ChatPromptRequest(BaseModel):
    message: str
    model: str | None = None
    thread_id: str | None = None


# ---------------------------------------------------------------------------
# Thread CRUD Endpoints
# ---------------------------------------------------------------------------

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


@router.patch("/threads/{thread_id}")
def rename_thread(
    thread_id: str,
    payload: RenameThreadRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Rename a conversation thread with length validation
    and user ownership enforcement.
    """
    user_payload = session_user_payload(request)
    if not user_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user_email = user_payload.get("email")
    user_sub = str(user_payload.get("sub")) if user_payload.get("sub") else None

    new_name = payload.name.strip()

    # 1. 校验：名称不能为空
    if not new_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation title cannot be empty.",
        )

    # 2. 校验：不能超过 50 个字符
    if len(new_name) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversation title cannot exceed 50 characters (current length: {len(new_name)}).",
        )

    # 3. 校验所有权并更新
    thread = db.execute(
        text("""
            SELECT id, "userIdentifier" FROM threads
            WHERE id = :thread_id AND ("userIdentifier" = :user_email OR "userIdentifier" = :user_sub)
        """),
        {"thread_id": thread_id, "user_email": user_email, "user_sub": user_sub},
    ).fetchone()

    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you do not have permission to modify it.",
        )

    try:
        db.execute(
            text('UPDATE threads SET name = :name WHERE id = :thread_id'),
            {"name": new_name, "thread_id": thread_id},
        )
        db.commit()
        return JSONResponse(content={"status": "success", "id": thread_id, "name": new_name})
    except Exception as e:
        db.rollback()
        logger.exception("Failed to rename thread: %s", e)
        raise HTTPException(status_code=500, detail="Database error occurred while renaming.")


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


# ---------------------------------------------------------------------------
# Streaming Chat & Fallback Endpoints
# ---------------------------------------------------------------------------

@router.post("/stream")
async def chat_stream_endpoint(
    payload: ChatPromptRequest,
    request: Request,
):
    """
    Streaming endpoint integrated with Grounding Gate and sidebar persistence.
    """
    user_payload = session_user_payload(request)
    user_identifier = (
        (user_payload.get("email") or str(user_payload.get("sub")))
        if user_payload
        else "anonymous"
    )
    thread_id = payload.thread_id or str(uuid.uuid4())

    try:
        with SessionLocal() as db:
            existing_thread = db.execute(
                text('SELECT id FROM threads WHERE id = :tid'),
                {"tid": thread_id}
            ).fetchone()

            if not existing_thread:
                title = payload.message.strip()[:28]
                db.execute(
                    text("""
                        INSERT INTO threads (id, "userIdentifier", name, "createdAt")
                        VALUES (:id, :uid, :name, NOW())
                    """),
                    {"id": thread_id, "uid": user_identifier, "name": title}
                )

            db.execute(
                text("""
                    INSERT INTO steps (id, "threadId", name, type, output, "createdAt")
                    VALUES (:id, :tid, 'user', 'user_message', :output, NOW())
                """),
                {"id": str(uuid.uuid4()), "tid": thread_id, "output": payload.message}
            )
            db.commit()
    except Exception as e:
        logger.exception("Failed to persist thread or user step: %s", e)

    async def event_generator():
        yield f"data: {json.dumps({'thread_id': thread_id})}\n\n"

        retrieved_chunks = []
        try:
            retrieved_chunks = retrieve(payload.message)
        except Exception as e:
            logger.warning("Retrieval failed: %s", e)

        gate_block = evaluate_grounding_gate(payload.message, retrieved_chunks)
        if gate_block:
            refusal_text = gate_block["output"]
            for char in refusal_text:
                yield f"data: {json.dumps({'token': char})}\n\n"
                await asyncio.sleep(0.01)

            yield f"data: {json.dumps({'sources': []})}\n\n"
            yield "data: [DONE]\n\n"

            try:
                with SessionLocal() as db:
                    db.execute(
                        text("""
                            INSERT INTO steps (id, "threadId", name, type, output, "createdAt")
                            VALUES (:id, :tid, 'Alfa Focus Assistant', 'assistant_message', :output, NOW())
                        """),
                        {"id": str(uuid.uuid4()), "tid": thread_id, "output": refusal_text}
                    )
                    db.commit()
            except Exception as e:
                logger.exception("Failed to persist refusal step: %s", e)
            return

        context = format_retrieved_context(retrieved_chunks)
        raw_answer = ""
        try:
            for token in generate_response_stream(
                query=payload.message,
                context=context,
                model=payload.model,
            ):
                raw_answer += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            cleaned_answer, valid_cites, invalid_cites = verify_and_clean_citations(
                raw_answer, len(retrieved_chunks)
            )
            if invalid_cites:
                logger.warning("Unverified citations flagged: %s", invalid_cites)

            unique_sources = {}
            for c in retrieved_chunks:
                if c.filename and c.filename not in unique_sources:
                    unique_sources[c.filename] = {
                        "title": c.source_label or c.filename,
                        "filename": c.filename,
                        "url": f"/static/docs/{c.filename}" if hasattr(c, "filename") else "#"
                    }

            yield f"data: {json.dumps({'sources': list(unique_sources.values())})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as ge:
            logger.exception("Generator streaming error: %s", ge)
            yield f"data: {json.dumps({'error': str(ge)})}\n\n"

        finally:
            final_content = cleaned_answer if 'cleaned_answer' in locals() and cleaned_answer else raw_answer
            if final_content.strip():
                try:
                    with SessionLocal() as db:
                        db.execute(
                            text("""
                                INSERT INTO steps (id, "threadId", name, type, output, "createdAt")
                                VALUES (:id, :tid, 'Alfa Focus Assistant', 'assistant_message', :output, NOW())
                            """),
                            {"id": str(uuid.uuid4()), "tid": thread_id, "output": final_content}
                        )
                        db.commit()
                except Exception as e:
                    logger.exception("Failed to persist assistant response step: %s", e)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("")
@router.post("/")
async def chat_standard_fallback_endpoint(payload: ChatPromptRequest, request: Request):
    """
    Non-streaming fallback endpoint to eliminate 405 errors
    when streaming is unavailable.
    """
    try:
        reply = generate_response(query=payload.message, model=payload.model)
        return JSONResponse(content={"output": reply})
    except Exception as e:
        logger.exception("Fallback chat error: %s", e)
        return JSONResponse(
            status_code=500,
            content={"output": f"Unable to generate response: {str(e)}"},
        )