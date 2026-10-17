import json

from scripts import evaluation_report as report


def _result(case_id, model, **overrides):
    result = {
        "id": case_id,
        "class": "C1",
        "question": f"Question {case_id}?",
        "must_refuse": False,
        "model_name": model,
        "retrieved_files": ["a.txt"],
        "metrics": {
            "answer_returned": True,
            "expected_source_hit": True,
            "top1_source_hit": True,
            "recall_at_k": 1.0,
            "reciprocal_rank": 1.0,
            "citation_present": True,
            "citation_valid": True,
            "refused": False,
            "refusal_correct": True,
            "provider_available": True,
        },
        "judge": {"correctness": 4, "faithfulness": 5},
        "latency_ms": 1000,
        "status": "ok",
    }
    result["metrics"].update(overrides.pop("metrics", {}))
    result.update(overrides)
    return result


def test_summarise_rates_and_refusal_scores():
    results = [
        _result("A", "m", latency_ms=1000),
        _result("B", "m", latency_ms=3000, metrics={"expected_source_hit": False, "reciprocal_rank": 0.0}),
        _result(
            "C",
            "m",
            must_refuse=True,
            latency_ms=2000,
            metrics={"expected_source_hit": None, "reciprocal_rank": None, "refused": True},
        ),
    ]

    summary = report.summarise(results)

    assert summary["source_hit"] == 0.5
    assert summary["mrr"] == 0.5
    assert summary["refusal_recall"] == 1.0
    assert summary["refusal_precision"] == 1.0
    assert summary["p50_latency_ms"] == 2000
    assert summary["p95_latency_ms"] == 3000
    assert summary["judge_correctness"] == 4


def test_case_failures_names_the_failed_metric():
    missed = _result("A", "m", must_refuse=True, metrics={"refused": False, "refusal_correct": False})
    bad_citation = _result("B", "m", metrics={"citation_valid": False, "invalid_citations": [7]})

    assert "missed refusal" in report.case_failures(missed)
    assert "invalid citations [7]" in report.case_failures(bad_citation)
    assert report.case_failures(_result("C", "m")) == []


def test_write_report_compares_models(tmp_path):
    paths = []

    for model in ["model-a", "model-b"]:
        path = tmp_path / f"{model}.jsonl"
        path.write_text(
            "\n".join(json.dumps(_result(i, model)) for i in ["A", "B"]) + "\n",
            encoding="utf-8",
        )
        paths.append(path)

    output = report.write_report(paths, tmp_path / "report.md", title="Test report")
    text = output.read_text(encoding="utf-8")

    assert "# Test report" in text
    assert "| Metric | `model-a` | `model-b` |" in text
    assert "No failed cases." in text
