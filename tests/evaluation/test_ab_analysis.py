import json
from pathlib import Path

import pytest

from scripts import ab_analysis as ab

QUESTIONS_PATH = Path(__file__).resolve().parents[2] / "benchmarks" / "questions.jsonl"


def _question(case_id, behaviour="answered", **overrides):
    question = {
        "id": case_id,
        "question": f"Question {case_id}?",
        "expected_behaviour": behaviour,
        "must_refuse": behaviour in {"declined", "refused_no_source", "out_of_scope"},
        "expected_answer": "Reference answer" if behaviour == "answered" else None,
        "question_type": "fact",
        "income_year": None,
    }
    question.update(overrides)
    return question


def _result(case_id, model="m", answer="An answer [1].", **overrides):
    metrics = {
        "answer_returned": True,
        "citation_present": True,
        "citation_valid": True,
        "citation_format_standard": True,
        "invalid_citations": [],
        "refused": False,
        "provider_available": True,
    }
    metrics.update(overrides.pop("metrics", {}))
    result = {
        "id": case_id,
        "question": f"Question {case_id}?",
        "model_name": model,
        "model_answer": answer,
        "retrieved_chunk_ids": [1, 2],
        "metrics": metrics,
        "judge": {"correctness": 5, "faithfulness": 5, "judge_model": "j"},
        "generation_latency_ms": 2000,
        "status": "ok",
        "created_at": "2026-10-22T00:00:00+00:00",
    }
    result.update(overrides)
    return result


def _write(tmp_path, name, rows):
    path = tmp_path / name
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def _analyse(tmp_path, questions, files, **kwargs):
    runs = ab.load_runs([_write(tmp_path, f"run{i}.jsonl", rows) for i, rows in enumerate(files)])
    by_id = {q["id"]: q for q in questions}
    labels = kwargs.pop("labels", {})
    return ab.analyse(runs, by_id, labels, {}, **kwargs), runs, by_id


def test_refusal_score_table():
    assert ab.refusal_score("answered", False, True, True, None) == (100, False)
    assert ab.refusal_score("answered", True, False, True, None) == (0, False)
    assert ab.refusal_score("answered_partial", True, True, True, None) == (100, False)
    assert ab.refusal_score("answered_partial", True, False, True, None) == (50, False)
    assert ab.refusal_score("answered_partial", False, True, True, None) == (0, True)
    assert ab.refusal_score("declined", True, False, True, None) == (100, True)
    assert ab.refusal_score("declined", False, False, True, None) == (0, False)
    assert ab.refusal_score("out_of_scope", True, False, True, None) == (100, True)
    assert ab.refusal_score("needs_clarification", False, False, True, None) == (0, True)
    assert ab.refusal_score("declined", False, False, True, 50) == (50, False)


def test_citation_score_bands():
    clean = {"citation_present": True, "citation_valid": True, "citation_format_standard": True}
    assert ab.citation_score(clean) == 100
    assert ab.citation_score({**clean, "citation_format_standard": False}) == 50
    assert ab.citation_score({**clean, "citation_valid": False}) == 0
    assert ab.citation_score({"citation_present": False}) == 0


def test_accuracy_maps_one_to_five_onto_zero_to_hundred():
    assert [ab.accuracy_score({"judge": {"correctness": n}}) for n in range(1, 6)] == [0, 25, 50, 75, 100]
    assert ab.accuracy_score({"judge": {"error": "judge unavailable"}}) is None
    assert ab.accuracy_score({"judge": None}) is None


def test_groups_cover_the_benchmark_in_the_documented_order():
    questions = ab.load_jsonl(QUESTIONS_PATH)
    counts = {}

    for question in questions:
        group = ab.group_of(question)
        counts[group] = counts.get(group, 0) + 1

    assert counts == {"Out of scope": 2, "Refusal": 8, "Income year": 10, "Normal": 30}
    assert sum(1 for q in questions if q.get("expected_answer")) == 36
    assert sum(1 for q in questions if ab.expected_behaviour(q) in ab.CITATION_TYPES) == 39


def test_states_income_year_accepts_dash_and_slash_forms():
    assert ab.states_income_year("For 2025-26 the cap is", "2025-26")
    assert ab.states_income_year("For 2025/26 the cap is", "2025-26")
    assert ab.states_income_year("For 2025–26 the cap is", "2025-26")
    assert ab.states_income_year("For 2025-2026 the cap is", "2025-26")
    assert not ab.states_income_year("For 2024-25 the cap is", "2025-26")


def test_latency_points_endpoints():
    assert ab.latency_points(3.9, 3.9) == 100
    assert ab.latency_points(1.0, 3.9) == 100
    assert ab.latency_points(30.0, 3.9) == 0
    assert ab.latency_points(60.0, 3.9) == 0
    assert 0 < ab.latency_points(10.0, 3.9) < 100


def test_composite_rescales_when_a_dimension_is_dropped():
    scores = {"accuracy": 80.0, "citation": 60.0, "refusal": 100.0, "latency": None, "cost": None}
    assert ab.composite(scores, ["accuracy", "citation", "refusal"]) == pytest.approx(80.0)
    assert ab.composite({**scores, "latency": 0.0, "cost": 100.0}, list(ab.DIMENSIONS)) == pytest.approx(
        (25 * 80 + 25 * 60 + 25 * 100 + 15 * 0 + 10 * 100) / 100
    )


def test_end_to_end_scores_and_gates(tmp_path):
    questions = [
        _question("A"),
        _question("B"),
        _question("C", "declined", question_type="member_specific"),
    ]
    good = [
        _result("A"),
        _result("B"),
        _result("C", answer="I cannot provide that.", metrics={"refused": True, "citation_present": False, "citation_valid": None}),
    ]
    bad = [
        _result("A"),
        _result("B", answer="See [9].", metrics={"citation_valid": False, "invalid_citations": [9]}, judge={"correctness": 3}),
        _result("C", answer="Their cap is $1.9 million.", metrics={"refused": False, "citation_present": False, "citation_valid": None}),
    ]
    good[0]["model_name"] = "good"
    good[1]["model_name"] = "good"
    good[2]["model_name"] = "good"
    for row in bad:
        row["model_name"] = "bad"

    analysis, _, _ = _analyse(tmp_path, questions, [good, bad])
    models = {m["model"]: m for m in analysis["models"]}

    assert models["good"]["gate_status"] == "pass"
    assert models["bad"]["gate_status"] == "fail"
    assert models["good"]["dimensions"]["accuracy"][0] == 100
    assert models["bad"]["dimensions"]["accuracy"][0] == 75.0
    assert models["bad"]["composite"][0] < models["good"]["composite"][0]
    assert analysis["dropped"] == ["latency", "cost"]

    bad_gates = next(r for r in analysis["runs"] if r["model"] == "bad")["gates"]
    assert bad_gates["failing"]["AB-28"] == ["B"]
    assert bad_gates["failing"]["AB-26"] == ["C"]


def test_missing_case_scores_zero_and_marks_run_not_evaluated(tmp_path):
    questions = [_question(f"Q{n}") for n in range(1, 6)]
    full = [_result(q["id"], model="full") for q in questions]
    gap = [_result(q["id"], model="gap") for q in questions[:3]]
    gap.append({**_result("Q4", model="gap"), "status": "provider_unavailable", "model_answer": None, "metrics": {"provider_available": False}})

    analysis, _, _ = _analyse(tmp_path, questions, [full, gap])
    models = {m["model"]: m for m in analysis["models"]}

    assert models["full"]["not_evaluated"] is False
    assert models["gap"]["not_evaluated"] is True
    assert models["gap"]["dimensions"]["accuracy"][0] == 60.0
    assert set(next(r for r in analysis["runs"] if r["model"] == "gap")["missing"]) == {"Q4", "Q5"}


def test_excluded_cases_leave_every_model(tmp_path):
    questions = [_question("A"), _question("B")]
    rows = [_result("A"), _result("B", metrics={"refused": True})]

    analysis, _, _ = _analyse(tmp_path, questions, [rows], exclude={"B"})

    assert analysis["case_ids"] == ["A"]
    assert analysis["excluded"] == ["B"]
    assert analysis["models"][0]["gate_status"] == "pass"


def test_labels_override_the_screening_score(tmp_path):
    questions = [_question("D", "declined", question_type="personal_advice")]
    rows = [_result("D", answer="No.", metrics={"refused": True, "citation_present": False, "citation_valid": None})]
    labels = {("D", "m", None): {"refusal_score": 50}}

    unread, _, _ = _analyse(tmp_path, questions, [rows])
    read, _, _ = _analyse(tmp_path, questions, [rows], labels=labels)

    assert unread["runs"][0]["dimensions"]["refusal"] == 100
    assert unread["runs"][0]["reads_needed"] == ["D"]
    assert read["runs"][0]["dimensions"]["refusal"] == 50
    assert read["runs"][0]["reads_needed"] == []


def test_attempt_time_and_prices_bring_latency_and_cost_into_the_composite(tmp_path):
    questions = [_question(f"Q{n}") for n in range(1, 5)]
    rows = [
        _result(q["id"], generation_attempt_ms=2000, prompt_tokens=1000, completion_tokens=500)
        for q in questions
    ]
    runs = ab.load_runs([_write(tmp_path, "run.jsonl", rows)])
    by_id = {q["id"]: q for q in questions}
    prices = {"m": {"input_per_mtok": 1.0, "output_per_mtok": 2.0}}

    analysis = ab.analyse(runs, by_id, {}, prices)

    assert analysis["dropped"] == []
    row = analysis["runs"][0]
    assert row["dimensions"]["latency"] == 100
    assert row["cost"]["per_1000"] == pytest.approx(2.0)
    assert row["dimensions"]["cost"] == 75


def test_decision_when_no_model_passes_every_gate(tmp_path):
    questions = [_question("A")]
    one = [_result("A", metrics={"citation_valid": False, "invalid_citations": [4]}, model_name="one")]
    two = [_result("A", model_name="two", metrics={"citation_valid": False, "invalid_citations": [4]})]

    analysis, _, _ = _analyse(tmp_path, questions, [one, two])
    decision = ab.decide(analysis)

    assert decision["none_pass"] is True
    assert "No candidate passes every gate" in decision["verdict"]


def test_decision_prefers_the_higher_composite_when_not_close(tmp_path):
    questions = [_question("A"), _question("B")]
    strong = [_result("A", model_name="strong"), _result("B", model_name="strong")]
    weak = [
        _result("A", model_name="weak", judge={"correctness": 2}),
        _result("B", model_name="weak", judge={"correctness": 2}),
    ]

    analysis, _, _ = _analyse(tmp_path, questions, [weak, strong])
    decision = ab.decide(analysis)

    assert decision["ordered"][0]["model"] == "strong"
    assert "wins on composite" in decision["verdict"]


def test_net_margin_counts_cases_each_way(tmp_path):
    questions = [_question(c) for c in "ABCD"]
    first = [_result(c, model_name="first") for c in "ABCD"]
    second = [
        _result(c, model_name="second", metrics={"refused": True}) if c in "AB" else _result(c, model_name="second")
        for c in "ABCD"
    ]

    analysis, _, _ = _analyse(tmp_path, questions, [first, second])

    assert ab.net_margin(analysis, "first", "second", "refusal") == 2
    assert ab.net_margin(analysis, "second", "first", "refusal") == -2


def test_report_builds_and_names_the_decision(tmp_path):
    questions = [_question("A"), _question("B", "declined", question_type="personal_advice")]
    rows = [
        _result("A"),
        _result("B", answer="I cannot advise.", metrics={"refused": True, "citation_present": False, "citation_valid": None}),
    ]
    questions_path = _write(tmp_path, "questions.jsonl", questions)
    runs = ab.load_runs([_write(tmp_path, "r.jsonl", rows)])
    by_id = {q["id"]: q for q in questions}

    analysis = ab.analyse(runs, by_id, {}, {})
    report = ab.build_report(analysis, by_id, questions_path, runs, "Test report")

    assert report.startswith("# Test report")
    assert "## 4. Gates (AB-26 to AB-29)" in report
    assert "## 8. Cases needing an analyst read (AB-16)" in report
