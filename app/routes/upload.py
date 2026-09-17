from pathlib import Path
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client

router = APIRouter()


BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@router.get("/upload", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="upload.html")

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")
# Examples
# @router.get("/upload")
# def upload_page():
#     ...

# @router.post("/upload")
# def upload_document():
#     ...

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase credentials not configured.")
    return create_client(url, key)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        supabase = get_supabase_client()
        bucket_name = os.getenv("SUPABASE_BUCKET", "documents")

        unique_prefix = str(uuid.uuid4())[:8]
        file_bytes = await file.read()
        storage_path = f"raw/{unique_prefix}_{file.filename}"

        # 1. Store raw file in Supabase Storage
        supabase.storage.from_(bucket_name).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.content_type or "application/octet-stream"}
        )

        # 2. Insert record matching teammate's table schema
        doc_record = {
            "filename": file.filename,
            "source_label": file.filename,
            "storage_path": storage_path,
            "status": "pending",
            "uploaded_by": "user",
            "uploaded_at": datetime.utcnow().isoformat()
        }

        res = supabase.table("documents").insert(doc_record).execute()
        return {
            "message": "File uploaded successfully",
            "document": res.data[0] if res.data else doc_record
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
def list_documents():
    try:
        supabase = get_supabase_client()
        res = supabase.table("documents").select("*").order("id", desc=True).execute()
        return {"documents": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/status")
def get_document_status(document_id: int):
    try:
        supabase = get_supabase_client()
        res = supabase.table("documents").select("id", "filename", "status", "uploaded_at").eq("id", document_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Document not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))