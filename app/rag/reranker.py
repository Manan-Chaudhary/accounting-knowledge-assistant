
import logging
import os
from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

DEFAULT_RERANKER_MODEL = (
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


@lru_cache(maxsize=1)
def _load_model() -> CrossEncoder:
    """Load the reranker once per application process."""
    model_name = os.getenv(
        "RERANKER_MODEL",
        DEFAULT_RERANKER_MODEL,
    )

    logger.info("Loading reranker model: %s", model_name)

    return CrossEncoder(model_name, max_length=512)


def rerank_chunks(
    query: str,
    chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    """
    Rerank retrieved chunks by query relevance.

    Returns the original chunk objects in their new order,
    preserving their IDs, content and source metadata.
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    if not chunks:
        return []

    model = _load_model()

    pairs = [
        (query.strip(), chunk.content)
        for chunk in chunks
    ]

    scores = model.predict(pairs)

    if len(scores) != len(chunks):
        raise RuntimeError(
            "Reranker returned an unexpected number of scores."
        )

    ranked = sorted(
        zip(chunks, scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )

    logger.info(
        "Reranked %s candidate chunks",
        len(ranked),
    )

    return [chunk for chunk, _score in ranked]