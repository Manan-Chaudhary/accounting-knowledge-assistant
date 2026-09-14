from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from chainlit.utils import mount_chainlit
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.routes.upload import router as upload_router
from app.routes.testing import router as testing_router
from app.routes.home import router as home_router
from app.routes.integration import router as integration_router


app = FastAPI()

# Routers for file upload and LLM testing endpoints
app.include_router(upload_router)
app.include_router(testing_router)
app.include_router(home_router)
app.include_router(integration_router)

@app.get("/")
def root():
    return RedirectResponse(url="/home")

# mounts CSS for all
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount the Chainlit app located at app/chainlit/chainlit_app.py -> needs to be last
mount_chainlit(app=app, target="app/chainlit/chainlit_app.py", path="/chat")