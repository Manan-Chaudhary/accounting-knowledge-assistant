from app.evaluation import harness
from app.rag.retriever import RetrievedChunk


def test_run_case_captures_response_and_retrieval(monkeypatch):
    chunks = [
        RetrievedChunk(
            chunk_id=101,
            document_id=8,
            chunk_index=0,
            content="Example accounting guidance.",
            filename="ato-example.txt",
            source_label="ATO guidance",
            distance=0.10,
        )
    ]

    monkeypatch.setattr(
        harness,
        "retrieve",
        lambda query, top_k: chunks,
    )

    monkeypatch.setattr(
        harness,
        "generate_with_model",
        lambda query, context, model: (
            "The retrieved guidance supports this answer [1]."
        ),
    )

    case = {
        "id": "TEST-001",
        "class": "C1",
        "question": "Test accounting question?",
        "expected_source": "ato-example.txt",
        "expected_outcome": "Grounded response",
        "must_refuse": False,
    }

    result = harness.run_case(
        case=case,
        model="test-model",
        top_k=6,
    )

    assert result["id"] == "TEST-001"
    assert result["model_name"] == "test-model"
    assert result["retrieved_chunk_ids"] == [101]
    assert result["retrieved_files"] == ["ato-example.txt"]

    assert result["metrics"]["answer_returned"] is True
    assert result["metrics"]["expected_source_hit"] is True
    assert result["metrics"]["citation_present"] is True


def test_expected_source_miss(monkeypatch):
    chunks = [
        RetrievedChunk(
            chunk_id=102,
            document_id=9,
            chunk_index=0,
            content="Different guidance.",
            filename="wrong-source.txt",
            source_label=None,
            distance=0.20,
        )
    ]

    monkeypatch.setattr(
        harness,
        "retrieve",
        lambda query, top_k: chunks,
    )

    monkeypatch.setattr(
        harness,
        "generate_with_model",
        lambda query, context, model: (
            "Answer without citation."
        ),
    )

    case = {
        "id": "TEST-002",
        "question": "Another question?",
        "expected_source": "expected-source.txt",
    }

    result = harness.run_case(
        case=case,
        model="test-model",
    )

    assert result["metrics"]["expected_source_hit"] is False
    assert result["metrics"]["citation_present"] is False
