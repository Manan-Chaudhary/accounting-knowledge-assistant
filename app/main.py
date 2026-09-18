import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from chainlit.utils import mount_chainlit
from fastapi.staticfiles import StaticFiles

from app.routes.upload import router as upload_router
from app.routes.testing import router as testing_router
from app.routes.home import router as home_router
from app.routes.integration import router as integration_router
from app.routes.auth import router as auth_router

FRONTEND_DIST = "frontend/dist"


app = FastAPI()

# Routers for file upload and LLM testing endpoints
app.include_router(upload_router)
app.include_router(testing_router)
app.include_router(home_router)
app.include_router(integration_router)

# mounts CSS for all
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount the Chainlit app located at app/chainlit/chainlit_app.py -> needs to be last
mount_chainlit(app=app, target="app/chainlit/chainlit_app.py", path="/chat")
# application sign in auth
app.include_router(auth_router)


# React SPA build (frontend/dist) -> registered last: it's a catch-all over
# every remaining GET, so anything above (API routers, /static, /chat, /login)
# has to be matched first or this swallows those requests too. Serves the
# real file when the request matches one in dist/ (JS/CSS bundle, favicon,
# etc.), otherwise falls back to index.html so React Router can handle a
# direct hit or refresh on a client-side route like /home or /docs.
@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    candidate = os.path.join(FRONTEND_DIST, full_path)
    if full_path and os.path.isfile(candidate):
        return FileResponse(candidate)
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))