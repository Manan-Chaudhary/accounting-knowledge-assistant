
from unittest.mock import patch

from app.rag.retriever import RetrievedChunk
from app.rag.reranker import rerank_chunks


def make_chunk(chunk_id: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=100 + chunk_id,
        chunk_index=chunk_id - 1,
        content=f"Example accounting content {chunk_id}",
        filename=f"document_{chunk_id}.pdf",
        source_label=f"Source {chunk_id}",
        distance=0.2,
    )


def test_reranker_sorts_by_relevance_score():
    chunks = [make_chunk(1), make_chunk(2), make_chunk(3)]

    with patch(
        "app.rag.reranker._load_model"
    ) as load_model:
        load_model.return_value.predict.return_value = [
            0.2, 0.9, 0.5
        ]

        results = rerank_chunks(
            "What are the tax rules?",
            chunks,
        )

    assert [chunk.chunk_id for chunk in results] == [2, 3, 1]


def test_reranker_preserves_original_chunk_metadata():
    chunk = make_chunk(1)

    with patch(
        "app.rag.reranker._load_model"
    ) as load_model:
        load_model.return_value.predict.return_value = [0.8]

        results = rerank_chunks("Tax question", [chunk])

    assert results[0] is chunk
    assert results[0].document_id == 101
    assert results[0].chunk_index == 0
    assert results[0].filename == "document_1.pdf"
    assert results[0].source_label == "Source 1"


def test_reranker_handles_empty_candidates():
    assert rerank_chunks("Tax question", []) == []