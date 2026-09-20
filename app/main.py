import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from chainlit.utils import mount_chainlit
from starlette.middleware.sessions import SessionMiddleware

from app.auth.secrets import SESSION_COOKIE_NAME, get_session_secret
from app.config import settings
from app.routes.auth import router as auth_router
from app.routes.upload import router as upload_router
from app.routes.testing import router as testing_router
from app.routes.home import router as home_router
from app.routes.integration import router as integration_router

logger = logging.getLogger(__name__)

FRONTEND_DIST = "frontend/dist"

app = FastAPI()

# FastAPI owns the session cookie (AU-83). Chainlit trusts it via
# header_auth_callback (AU-84). App-wide route locking (AU-85) is still TODO —
# React RequireAuth is frontend-only until middleware lands.
session_secret = get_session_secret()
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie=SESSION_COOKIE_NAME,
    same_site="lax",
    https_only=settings.ENVIRONMENT == "production",
    max_age=settings.SESSION_MAX_AGE_SECONDS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# API / backend routers must register before the SPA catch-all below.
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(testing_router)
#app.include_router(home_router)
app.include_router(integration_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

if settings.CHAINLIT_AUTH_SECRET:
    os.environ["CHAINLIT_AUTH_SECRET"] = settings.CHAINLIT_AUTH_SECRET
elif not os.environ.get("CHAINLIT_AUTH_SECRET"):
    if settings.ENVIRONMENT == "production":
        raise RuntimeError(
            "CHAINLIT_AUTH_SECRET is not set. Refusing to mount Chainlit in production without it."
        )
    logger.warning(
        "CHAINLIT_AUTH_SECRET is not set — Chainlit /chat remains public. "
        "Set it in .env to enable header auth against the FastAPI session (AU-86)."
    )

# Mount Chainlit before the SPA catch-all so /chat is not swallowed.
mount_chainlit(app=app, target="app/chainlit/chainlit_app.py", path="/chat")

# React SPA build (frontend/dist). Catch-all must stay last.
@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    candidate = os.path.join(FRONTEND_DIST, full_path)
    if full_path and os.path.isfile(candidate):
        return FileResponse(candidate)
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
