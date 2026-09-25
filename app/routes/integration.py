import hmac

from fastapi import APIRouter, Depends, Header
from fastapi import HTTPException
from app.services.document_service import process_document
from app.config import settings

router = APIRouter(prefix="/api", tags=["integration"])


def verify_n8n_secret(x_n8n_secret: str = Header(None)):
    """
    Shared-secret check for internal n8n -> FastAPI calls.

    These requests come from n8n's HTTP Request node (server-to-server,
    inside Docker) so they never carry a browser session cookie, and
    /api/n8n/ is exempted from the app-wide session-auth middleware in
    main.py. This dependency is what actually protects the route instead.
    """
    if not x_n8n_secret or not settings.N8N_SHARED_SECRET or not hmac.compare_digest(
        x_n8n_secret, settings.N8N_SHARED_SECRET
    ):
        raise HTTPException(status_code=401, detail="Invalid n8n secret")


@router.get("/n8n-test")
def n8n_test():
    return {
        "status": "ok",
        "message": "FastAPI successfully reached from n8n"
    }


@router.post(
    "/n8n/process-document/{document_id}",
    dependencies=[Depends(verify_n8n_secret)],
)
def n8n_process_document(document_id: int):
    try:
        return process_document(document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))