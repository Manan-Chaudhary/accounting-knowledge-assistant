import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from supabase import create_client, Client
import httpx

router = APIRouter()

# /upload (GET, HTML) is now served by the React app
# (frontend/src/pages/Documents.tsx), retired here once the React page was
# validated as equivalent. POST /upload and GET /documents below are
# unchanged — the React page calls these same JSON endpoints.

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
            file_options={
                "content-type": file.content_type or "application/octet-stream"
            }
        )

        # 2. Insert document record
        doc_record = {
            "filename": file.filename,
            "source_label": file.filename,
            "storage_path": storage_path,
            "status": "pending",
            "uploaded_by": "user",
            "uploaded_at": datetime.utcnow().isoformat()
        }

        res = supabase.table("documents").insert(doc_record).execute()

        if not res.data:
            raise ValueError("Document record was not created.")

        document = res.data[0]
        document_id = document["id"]

        # 3. Trigger n8n document-processing workflow
        n8n_url = "http://n8n:5678/webhook/process-document"

        async with httpx.AsyncClient(timeout=10.0) as client:
            n8n_response = await client.post(
                n8n_url,
                json={"document_id": document_id}
            )

        if n8n_response.status_code >= 400:
            raise ValueError(
                f"n8n processing trigger failed: "
                f"{n8n_response.status_code} {n8n_response.text}"
            )

        return {
            "message": "File uploaded and processing started",
            "document": document
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