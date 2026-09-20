import chainlit as cl
from typing import Optional

from app.auth.chainlit_bridge import user_from_request_headers
from app.rag.generator import generate_response


@cl.header_auth_callback
def header_auth_callback(headers) -> Optional[cl.User]:
    """Accept the FastAPI aka_session cookie — Chainlit does not check passwords (AU-84)."""
    return user_from_request_headers(headers)


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
        msg.content = f"⚠️ error messeage: {str(e)}"

    await msg.update()
