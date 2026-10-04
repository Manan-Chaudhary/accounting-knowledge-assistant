import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select

from app.db.database import SessionLocal
from app.db.models import Document, DocumentChunk, EMBEDDING_DIM
from app.rag.embedder import embed_text


logger = logging.getLogger(__name__)


# Retrieval configuration
DEFAULT_DENSE_K = 10
DEFAULT_KEYWORD_K = 10
DEFAULT_TOP_K = 6
RRF_K = 60


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    filename: str
    source_label: Optional[str]
    distance: Optional[float] = None

    @property
    def similarity(self) -> Optional[float]:
        """
        Convert cosine distance to similarity.

        Keyword results do not have a cosine distance, so they
        return None.
        """
        if self.distance is None:
            return None

        return 1.0 - self.distance


def _validate_query(query: str) -> str:
    """
    Validate and normalise a retrieval query.
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    return query.strip()


def _validate_embedding(embedding: list[float]) -> None:
    """
    Ensure the embedding returned by BGE-M3 has the expected dimension.
    """

    if len(embedding) != EMBEDDING_DIM:
        raise ValueError(
            f"Unexpected query embedding dimension: "
            f"{len(embedding)}. "
            f"Expected {EMBEDDING_DIM}."
        )


def retrieve_dense(
    query: str,
    top_k: int = DEFAULT_DENSE_K,
) -> list[RetrievedChunk]:
    """
    Strategy 1: dense vector retrieval.

    Flow:
        query
        -> BGE-M3 embedding
        -> pgvector cosine search
        -> ready documents only
        -> top-k chunks
    """

    query = _validate_query(query)

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    query_embedding = embed_text(query)
    _validate_embedding(query_embedding)

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
            "Dense retrieval returned %s chunks for query",
            len(results),
        )

        return results

    except Exception:
        logger.exception(
            "Failed during dense retrieval"
        )
        raise

    finally:
        db.close()


def retrieve_keyword(
    query: str,
    top_k: int = DEFAULT_KEYWORD_K,
) -> list[RetrievedChunk]:
    """
    Strategy 2: PostgreSQL full-text / keyword retrieval.

    Exact terminology is particularly useful for accounting queries
    containing legislation names, section numbers, abbreviations,
    tax terminology, and other specialised phrases.
    """

    query = _validate_query(query)

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    db = SessionLocal()

    try:
        # PostgreSQL full-text search expressions.
        search_vector = func.to_tsvector(
            "english",
            DocumentChunk.content,
        )

        search_query = func.plainto_tsquery(
            "english",
            query,
        )

        keyword_score = func.ts_rank(
            search_vector,
            search_query,
        ).label("keyword_score")

        statement = (
            select(
                DocumentChunk,
                Document,
                keyword_score,
            )
            .join(
                Document,
                Document.id == DocumentChunk.document_id,
            )
            .where(
                Document.status == "ready",
                search_vector.op("@@")(search_query),
            )
            .order_by(keyword_score.desc())
            .limit(top_k)
        )

        rows = db.execute(statement).all()

        results: list[RetrievedChunk] = []

        for chunk, document, _score in rows:
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    filename=document.filename,
                    source_label=document.source_label,
                    distance=None,
                )
            )

        logger.info(
            "Keyword retrieval returned %s chunks for query",
            len(results),
        )

        return results

    except Exception:
        logger.exception(
            "Failed during keyword retrieval"
        )
        raise

    finally:
        db.close()


def reciprocal_rank_fusion(
    dense_results: list[RetrievedChunk],
    keyword_results: list[RetrievedChunk],
    rrf_k: int = RRF_K,
) -> list[RetrievedChunk]:
    """
    Combine dense and keyword retrieval results using
    Reciprocal Rank Fusion (RRF).

    RRF does not require the raw scores from the two retrieval
    systems to be comparable. Instead, it combines their rankings.

    RRF contribution:
        1 / (rrf_k + rank)
    """

    if rrf_k <= 0:
        raise ValueError("rrf_k must be greater than zero.")

    scores: dict[int, float] = {}
    chunks: dict[int, RetrievedChunk] = {}

    # Dense ranking
    for rank, chunk in enumerate(dense_results, start=1):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + (
            1.0 / (rrf_k + rank)
        )
        chunks[chunk.chunk_id] = chunk

    # Keyword ranking
    for rank, chunk in enumerate(keyword_results, start=1):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + (
            1.0 / (rrf_k + rank)
        )

        # Prefer the dense result when the same chunk exists in both
        # result sets because it contains the cosine distance.
        if chunk.chunk_id not in chunks:
            chunks[chunk.chunk_id] = chunk

    ranked_chunk_ids = sorted(
        scores,
        key=lambda chunk_id: scores[chunk_id],
        reverse=True,
    )

    results = [
        chunks[chunk_id]
        for chunk_id in ranked_chunk_ids
    ]

    logger.info(
        "RRF combined %s unique chunks",
        len(results),
    )

    return results


def retrieve_hybrid(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    dense_k: int = DEFAULT_DENSE_K,
    keyword_k: int = DEFAULT_KEYWORD_K,
) -> list[RetrievedChunk]:
    """
    Strategy 3: hybrid retrieval.

    Flow:
        query
        -> dense retrieval
        -> keyword retrieval
        -> Reciprocal Rank Fusion
        -> final top-k chunks
    """

    query = _validate_query(query)

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    if dense_k <= 0:
        raise ValueError("dense_k must be greater than zero.")

    if keyword_k <= 0:
        raise ValueError("keyword_k must be greater than zero.")

    dense_results = retrieve_dense(
        query=query,
        top_k=dense_k,
    )

    keyword_results = retrieve_keyword(
        query=query,
        top_k=keyword_k,
    )

    fused_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        keyword_results=keyword_results,
    )

    results = fused_results[:top_k]

    logger.info(
        "Hybrid retrieval returned %s chunks",
        len(results),
    )

    return results


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """
    Main retrieval entry point.

    The application uses hybrid retrieval by default:
        dense vector retrieval
        + keyword retrieval
        + RRF
        -> final top-k chunks
    """

    return retrieve_hybrid(
        query=query,
        top_k=top_k,
    )


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
    Retrieve relevant chunks using hybrid retrieval and return
    formatted context ready for the LLM.
    """

    chunks = retrieve(
        query=query,
        top_k=top_k,
    )

    return format_retrieved_context(chunks)