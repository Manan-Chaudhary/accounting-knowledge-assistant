import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Document, DocumentChunk, EMBEDDING_DIM
from app.rag.embedder import embed_text


logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 6


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    filename: str
    source_label: Optional[str]
    distance: float

    @property
    def similarity(self) -> float:
        return 1.0 - self.distance


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """
    Retrieve the most relevant document chunks for a user query.

    Flow:
    query
    -> BGE-M3 embedding
    -> pgvector cosine search
    -> ready documents only
    -> top-k chunks
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    query_embedding = embed_text(query)

    if len(query_embedding) != EMBEDDING_DIM:
        raise ValueError(
            f"Unexpected query embedding dimension: "
            f"{len(query_embedding)}. "
            f"Expected {EMBEDDING_DIM}."
        )

    db = SessionLocal()

    try:
        distance_expression = (
            DocumentChunk.embedding.cosine_distance(query_embedding)
        ).label("distance")

        statement = (
            select(
                DocumentChunk,
                Document,
                distance_expression,
            )
            .join(
                Document,
                Document.id == DocumentChunk.document_id,
            )
            .where(Document.status == "ready")
            .order_by(distance_expression)
            .limit(top_k)
        )

        rows = db.execute(statement).all()

        results: list[RetrievedChunk] = []

        for chunk, document, distance in rows:
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    filename=document.filename,
                    source_label=document.source_label,
                    distance=float(distance),
                )
            )

        logger.info(
            "Retrieved %s chunks for query",
            len(results),
        )

        return results

    except Exception:
        logger.exception(
            "Failed to retrieve document chunks for query"
        )
        raise

    finally:
        db.close()


def format_retrieved_context(
    chunks: list[RetrievedChunk],
) -> str:
    """
    Format retrieved chunks as numbered source blocks
    for the LLM prompt.
    """

    if not chunks:
        return (
            "No relevant document chunks were retrieved for this query. "
            "Do not answer using general knowledge. "
            "State that no supporting source was found."
        )

    context_blocks: list[str] = []

    for citation_number, chunk in enumerate(chunks, start=1):
        source = chunk.source_label or chunk.filename

        block = (
            f"[{citation_number}]\n"
            f"Source: {source}\n"
            f"File: {chunk.filename}\n"
            f"Document ID: {chunk.document_id}\n"
            f"Chunk: {chunk.chunk_index}\n"
            f"Content:\n{chunk.content}"
        )

        context_blocks.append(block)

    return "\n\n".join(context_blocks)


def retrieve_context(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> str:
    """
    Retrieve relevant chunks and return formatted
    context ready for the LLM.
    """

    chunks = retrieve(
        query=query,
        top_k=top_k,
    )

    return format_retrieved_context(chunks)