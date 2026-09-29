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


def _chunk(chunk_id, filename, distance=0.1):
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=chunk_id,
        chunk_index=0,
        content="Guidance text.",
        filename=filename,
        source_label=None,
        distance=distance,
    )


def test_retrieval_metrics_rank_and_recall():
    metrics = harness.retrieval_metrics(
        expected_sources=["a.txt", "b.txt"],
        retrieved_files=["x.txt", "a.txt", "a.txt"],
    )

    assert metrics["expected_source_hit"] is True
    assert metrics["top1_source_hit"] is False
    assert metrics["recall_at_k"] == 0.5
    assert metrics["reciprocal_rank"] == 0.5


def test_retrieval_metrics_not_applicable_without_expected_source():
    metrics = harness.retrieval_metrics([], ["x.txt"])

    assert all(value is None for value in metrics.values())


def test_citation_metrics_flags_markers_outside_retrieved_chunks():
    metrics = harness.citation_metrics("Rule one [1]. Rule two [4].", chunk_count=3)

    assert metrics["citation_present"] is True
    assert metrics["citation_valid"] is False
    assert metrics["invalid_citations"] == [4]


def test_citation_metrics_without_citations():
    metrics = harness.citation_metrics("No markers here.", chunk_count=3)

    assert metrics["citation_present"] is False
    assert metrics["citation_valid"] is None


def test_is_refusal_matches_prompt_templates():
    assert harness.is_refusal(
        "I could not find authority for this in the indexed sources, "
        "so I am not going to answer it."
    )
    assert harness.is_refusal("That figure is specific to the member.")
    assert not harness.is_refusal("For 2026-27 the cap is $2.1 million [1].")


def test_must_refuse_case_scores_refusal(monkeypatch):
    monkeypatch.setattr(harness, "retrieve", lambda query, top_k: [])
    monkeypatch.setattr(
        harness,
        "generate_with_model",
        lambda query, context, model: "I could not find authority for this.",
    )

    result = harness.run_case(
        case={"id": "T-REF", "question": "Confirm TR 2099/1.", "must_refuse": True},
        model="test-model",
    )

    assert result["metrics"]["refused"] is True
    assert result["metrics"]["refusal_correct"] is True
    assert result["metrics"]["expected_source_hit"] is None


def test_over_refusal_is_not_correct(monkeypatch):
    monkeypatch.setattr(harness, "retrieve", lambda query, top_k: [_chunk(1, "a.txt")])
    monkeypatch.setattr(
        harness,
        "generate_with_model",
        lambda query, context, model: "I could not find authority for this.",
    )

    result = harness.run_case(
        case={"id": "T-OVER", "question": "Q?", "expected_sources": ["a.txt"]},
        model="test-model",
    )

    assert result["metrics"]["refusal_correct"] is False


def test_judge_runs_only_with_expected_answer(monkeypatch):
    monkeypatch.setattr(harness, "retrieve", lambda query, top_k: [_chunk(1, "a.txt")])
    monkeypatch.setattr(
        harness,
        "generate_with_model",
        lambda query, context, model: "Answer [1].",
    )
    monkeypatch.setattr(
        harness,
        "complete_with_retry",
        lambda **kwargs: '{"correctness": 4, "faithfulness": 5, "reason": "ok"}',
    )

    judged = harness.run_case(
        case={"id": "T-J1", "question": "Q?", "expected_answer": "A."},
        model="test-model",
        judge_model="judge-model",
    )
    unjudged = harness.run_case(
        case={"id": "T-J2", "question": "Q?"},
        model="test-model",
        judge_model="judge-model",
    )

    assert judged["judge"]["correctness"] == 4
    assert judged["judge"]["faithfulness"] == 5
    assert unjudged["judge"] is None


def test_load_cases_accepts_single_expected_source(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text(
        '{"id": "A", "question": "Q1?", "expected_source": "a.txt"}\n'
        "\n"
        '{"id": "B", "question": "Q2?", "expected_sources": ["b.txt", "c.txt"]}\n',
        encoding="utf-8",
    )

    cases = harness.load_cases(path)

    assert [case["expected_sources"] for case in cases] == [["a.txt"], ["b.txt", "c.txt"]]


def test_run_suite_records_provider_failure(monkeypatch, tmp_path):
    from litellm.exceptions import ServiceUnavailableError

    def unavailable(**kwargs):
        raise ServiceUnavailableError(
            message="down", llm_provider="gemini", model="test-model"
        )

    questions = tmp_path / "cases.jsonl"
    questions.write_text('{"id": "A", "question": "Q?"}\n', encoding="utf-8")
    output = tmp_path / "results.jsonl"

    monkeypatch.setattr(harness, "run_case", unavailable)

    results = harness.run_suite(questions, output, model="test-model")

    assert results[0]["status"] == "provider_unavailable"
    assert results[0]["metrics"]["provider_available"] is False
    assert results[0]["run_id"]
    assert len(output.read_text(encoding="utf-8").splitlines()) == 1


def test_api_key_follows_model_prefix(monkeypatch):
    monkeypatch.setattr(harness.settings, "GEMINI_API_KEY", "gem")
    monkeypatch.setattr(harness.settings, "GROQ_API_KEY", "groq")

    assert harness.api_key_for("gemini/gemini-3.8-flash") == "gem"
    assert harness.api_key_for("groq/openai/gpt-oss-120b") == "groq"
    assert harness.api_key_for("unknown/model") is None

def test_judge_outage_keeps_the_answer(monkeypatch):
    from litellm.exceptions import ServiceUnavailableError

    def unavailable(**kwargs):
        raise ServiceUnavailableError(
            message="down", llm_provider="gemini", model="judge-model"
        )

    monkeypatch.setattr(harness, "retrieve", lambda query, top_k: [_chunk(1, "a.txt")])
    monkeypatch.setattr(
        harness,
        "generate_with_model",
        lambda query, context, model: "Answer [1].",
    )
    monkeypatch.setattr(harness, "complete_with_retry", unavailable)

    result = harness.run_case(
        case={"id": "T-J3", "question": "Q?", "expected_answer": "A."},
        model="test-model",
        judge_model="judge-model",
    )

    assert result["status"] == "ok"
    assert result["model_answer"] == "Answer [1]."
    assert "judge unavailable" in result["judge"]["error"]

def test_rate_limit_wait_uses_provider_hint():
    from litellm.exceptions import RateLimitError, ServiceUnavailableError

    hinted = RateLimitError(
        message="Rate limit reached. Please try again in 7.08s.",
        llm_provider="groq",
        model="m",
    )
    unhinted = RateLimitError(message="slow down", llm_provider="groq", model="m")
    unavailable = ServiceUnavailableError(message="down", llm_provider="gemini", model="m")

    assert harness.retry_wait_seconds(hinted, attempt=1) == 7.08 + 2
    assert harness.retry_wait_seconds(unhinted, attempt=2) == 30.0
    assert harness.retry_wait_seconds(unavailable, attempt=3) == 8

def test_nonstandard_citations_are_counted_but_flagged():
    metrics = harness.citation_metrics("Limit is $500,000\u30106\u2020L1-L2\u3011.", chunk_count=6)

    assert metrics["citation_present"] is True
    assert metrics["citation_valid"] is True
    assert metrics["citation_format_standard"] is False


def test_is_refusal_matches_observed_model_wording():
    assert harness.is_refusal("I could not locate any source in the provided context.")
    assert harness.is_refusal("I could not find any source that specifies the cap.")
    assert harness.is_refusal("I\u2019m unable to provide a personal transfer-balance cap.")


def test_rescore_updates_stored_metrics():
    stored = {
        "status": "ok",
        "must_refuse": True,
        "model_answer": "I could not locate any source for TR 2024/8.",
        "expected_sources": [],
        "retrieved_files": ["a.txt", "b.txt"],
        "metrics": {"refused": False, "refusal_correct": False},
    }

    rescored = harness.rescore(stored)

    assert rescored["metrics"]["refused"] is True
    assert rescored["metrics"]["refusal_correct"] is True
    assert rescored["metrics"]["citation_present"] is False