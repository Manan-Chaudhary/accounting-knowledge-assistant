from fastapi import APIRouter
from fastapi import HTTPException
from app.services.document_service import process_document

router = APIRouter(prefix="/api", tags=["integration"])


@router.get("/n8n-test")
def n8n_test():
    return {
        "status": "ok",
        "message": "FastAPI successfully reached from n8n"
    }



@router.post("/n8n/process-document/{document_id}")
def n8n_process_document(document_id: int):
    try:
        return process_document(document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    