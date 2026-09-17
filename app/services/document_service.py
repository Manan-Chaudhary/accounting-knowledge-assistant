from io import BytesIO

import pymupdf
from docx import Document as DocxDocument
from sqlalchemy import delete, select

from app.db.database import SessionLocal
from app.db.models import Document, DocumentChunk
from app.rag.embedder import embed_text
from app.services.storage_service import get_supabase_client
from app.config import settings


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from PDF, DOCX, or TXT files.
    """
    extension = filename.lower().split(".")[-1]

    if extension == "pdf":
        return _extract_pdf(file_bytes)

    if extension == "docx":
        return _extract_docx(file_bytes)

    if extension == "txt":
        return file_bytes.decode("utf-8", errors="replace").strip()

    raise ValueError(f"Unsupported file type: .{extension}")


def _extract_pdf(file_bytes: bytes) -> str:
    text_parts = []

    with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:
        for page in pdf:
            text_parts.append(page.get_text())

    return "\n".join(text_parts).strip()


def _extract_docx(file_bytes: bytes) -> str:
    document = DocxDocument(BytesIO(file_bytes))

    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    return "\n".join(paragraphs).strip()


def chunk_text(
    text: str,
    chunk_size: int = 2000,
    overlap: int = 200,
) -> list[str]:
    """
    Split text into overlapping character-based chunks.
    """
    if not text.strip():
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def process_document(document_id: int) -> dict:
    """
    Process one uploaded document:

    pending → processing → ready

    If processing fails:
    processing → failed
    and stores a readable failure reason.
    """

    db = SessionLocal()

    try:
        # 1. Find the document
        document = db.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

        if document is None:
            raise ValueError(f"Document {document_id} not found")

        # 2. Mark as processing
        document.status = "processing"
        document.failure_reason = None
        db.commit()

        # 3. Download the raw file from Supabase Storage
        supabase = get_supabase_client()

        file_bytes = supabase.storage.from_(
            settings.SUPABASE_BUCKET
        ).download(document.storage_path)

        if not file_bytes:
            raise ValueError("Downloaded file is empty")

        # 4. Extract text
        text = extract_text(file_bytes, document.filename)

        if not text.strip():
            raise ValueError("No readable text could be extracted from the document")

        # 5. Chunk the document
        chunks = chunk_text(text)

        if not chunks:
            raise ValueError("Document produced no usable chunks")

        # 6. Remove old chunks so reprocessing doesn't create duplicates
        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id
            )
        )
        db.commit()

        # 7. Generate embeddings and save chunks
        for index, chunk in enumerate(chunks):
            embedding = embed_text(chunk)

            if len(embedding) != 1024:
                raise ValueError(
                    f"Unexpected embedding dimension: {len(embedding)}"
                )

            db_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                embedding=embedding,
            )

            db.add(db_chunk)

        # 8. Save everything
        db.commit()

        # 9. Mark document ready
        document.status = "ready"
        document.failure_reason = None
        db.commit()

        return {
            "document_id": document.id,
            "filename": document.filename,
            "status": document.status,
            "chunk_count": len(chunks),
        }

    except Exception as e:
        db.rollback()

        # Try to record the failure
        try:
            document = db.execute(
                select(Document).where(Document.id == document_id)
            ).scalar_one_or_none()

            if document:
                document.status = "failed"
                document.failure_reason = str(e)
                db.commit()
        except Exception:
            db.rollback()

        raise

    finally:
        db.close()