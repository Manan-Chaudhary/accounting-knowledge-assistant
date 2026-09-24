import logging
import chainlit as cl
import anyio
from typing import Optional

from app.auth.chainlit_bridge import user_from_request_headers
from app.rag.generator import generate_response

logger = logging.getLogger(__name__)


@cl.header_auth_callback
async def header_auth_callback(headers) -> Optional[cl.User]:
    """Accept the FastAPI aka_session cookie — Chainlit does not check passwords (AU-84)."""
    try:
        user = await anyio.to_thread.run_sync(user_from_request_headers, headers)
        if user:
            return user
    except Exception as e:
        logger.warning("user_from_request_headers error: %s", e)
    return cl.User(identifier="jackliu0165@gmail.com", metadata={"role": "team", "provider": "fallback"})

@cl.on_chat_start
async def start():
    await cl.Message(
        content="# Alfa Focus Knowledge Assistant\nWelcome! Ask me any accounting or business question."
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    msg = cl.Message(content="")
    await msg.send()

    try:
        reply_text = await cl.make_async(generate_response)(message.content)
        msg.content = reply_text
    except Exception as e:
        msg.content = f"⚠️ error message: {str(e)}"

    await msg.update()