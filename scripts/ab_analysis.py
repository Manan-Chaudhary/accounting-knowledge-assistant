"""Score and compare model runs under docs/MODEL-AB-SCORING.md (AB-n rule ids).

Reads the JSONL result files written by scripts/run_evaluation.py and the
questions file, and computes every number from them. Nothing is typed in by
hand (AB-54): rerunning on the same files gives the same output.
"""

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

WEIGHTS = {"accuracy": 25, "citation": 25, "refusal": 25, "latency": 15, "cost": 10}
DIMENSIONS = list(WEIGHTS)
GATES = ["AB-26", "AB-27", "AB-28", "AB-29"]

REFUSAL_TYPES = {"declined", "refused_no_source", "out_of_scope", "answered_partial"}
ANSWER_TYPES = {"answered", "needs_clarification"}
CITATION_TYPES = {"answered", "answered_partial"}

RECALL_GATE = 0.95
PRECISION_GATE = 0.85
MAX_MISSING_SHARE = 0.04
CLOSE_COMPOSITE_GAP = 3.0
REAL_MARGIN = 3
REAL_LATENCY_DROP = 0.20
COLD_REQUESTS = 2
LATENCY_FLOOR_S = 30.0
P50_TARGET_S = 3.9
P95_TARGET_S = 5.9
COST_BANDS = [(1, 100), (5, 75), (20, 50), (50, 25)]

# Optional result fields that AB-7 asks the harness to add. Rename here if the
# harness writes them under other names.
F_TEMPERATURE = "temperature"
F_PROMPT_TOKENS = "prompt_tokens"
F_COMPLETION_TOKENS = "completion_tokens"
F_ANSWERED_BY = "answered_by"
F_ATTEMPT_MS = "generation_attempt_ms"

AMOUNT_PATTERN = re.compile(r"(\$\s?\d|\d\s?%|\d\s?per ?cent)", re.IGNORECASE)
COMMA_MARKER_PATTERN = re.compile(r"\[\d+\s*(?:,|-)\s*\d+")


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def file_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None

    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))

    return ordered[rank - 1]


def expected_behaviour(question: dict[str, Any]) -> str:
    declared = question.get("expected_behaviour")

    if declared:
        return declared

    return "declined" if question.get("must_refuse") else "answered"


def group_of(question: dict[str, Any]) -> str:
    """Section 8 group, applied in the order the document gives."""

    behaviour = expected_behaviour(question)

    if behaviour == "out_of_scope":
        return "Out of scope"

    if behaviour in {"declined", "refused_no_source"}:
        return "Refusal"

    if question.get("income_year") or question.get("question_type") in {
        "income_year",
        "missing_year",
    }:
        return "Income year"

    return "Normal"


GROUP_ORDER = ["Out of scope", "Refusal", "Income year", "Normal"]


def is_missing(result: dict[str, Any] | None) -> bool:
    if result is None:
        return True

    if result.get("status", "ok") != "ok":
        return True

    return not result.get("metrics", {}).get("provider_available", True)


def refusal_score(
    expected: str,
    refused: bool,
    cite_present: bool,
    cite_valid: bool,
    label_score: int | None,
) -> tuple[int | None, bool]:
    """Section 4.3 table: (score, needs an analyst read)."""

    if label_score is not None:
        return label_score, False

    cited = bool(cite_present and cite_valid)

    if expected == "answered":
        return (0 if refused else 100), False

    if expected == "answered_partial":
        if refused:
            return (100 if cited else 50), False
        return 0, True

    if expected in {"declined", "out_of_scope", "refused_no_source"}:
        return (100 if refused else 0), refused

    if expected == "needs_clarification":
        return 0, True

    return None, False


def citation_score(metrics: dict[str, Any]) -> int:
    """AB-11: 100 clean, 50 present and valid but non-standard, else 0."""

    if not metrics.get("citation_present"):
        return 0

    if metrics.get("citation_valid") is False:
        return 0

    if metrics.get("citation_format_standard") is False:
        return 50

    return 100


def accuracy_score(result: dict[str, Any]) -> int | None:
    """AB-8: (correctness - 1) x 25, or None when the judge gave no score."""

    judge = result.get("judge") or {}
    correctness = judge.get("correctness")

    if isinstance(correctness, (int, float)):
        return int(round((correctness - 1) * 25))

    return None


def states_income_year(answer: str, year: str) -> bool:
    match = re.match(r"(\d{4})\D+(\d{2,4})$", year.strip())

    if not match:
        return year in answer

    start, end = match.group(1), match.group(2)[-2:]
    pattern = rf"{start}\s*[-/–—]\s*(?:{start[:2]})?{end}"

    return bool(re.search(pattern, answer))


def label_key(case_id: str, model: str, run_no: int | None) -> tuple[str, str, int | None]:
    return (case_id, model, run_no)


def load_labels(path: str | Path | None) -> dict[tuple[str, str, int | None], dict[str, Any]]:
    if not path:
        return {}

    labels: dict[tuple[str, str, int | None], dict[str, Any]] = {}

    for row in load_jsonl(path):
        labels[label_key(row["id"], row["model"], row.get("run"))] = row

    return labels


def find_label(
    labels: dict[tuple[str, str, int | None], dict[str, Any]],
    case_id: str,
    model: str,
    run_no: int,
) -> dict[str, Any] | None:
    return labels.get(label_key(case_id, model, run_no)) or labels.get(
        label_key(case_id, model, None)
    )


def load_runs(paths: list[str | Path]) -> list[dict[str, Any]]:
    """One entry per result file; runs of the same model are numbered 1, 2, 3."""

    counts: dict[str, int] = defaultdict(int)
    runs = []

    for path in paths:
        results = load_jsonl(path)

        if not results:
            continue

        model = results[0].get("model_name") or Path(path).stem
        counts[model] += 1

        runs.append(
            {
                "model": model,
                "run_no": counts[model],
                "path": str(path),
                "results": {r["id"]: r for r in results},
                "order": [r["id"] for r in results],
            }
        )

    return runs


def percent_missing_limit(case_total: int) -> int:
    return math.floor(MAX_MISSING_SHARE * case_total)


def score_run(
    run: dict[str, Any],
    questions: dict[str, dict[str, Any]],
    case_ids: list[str],
    labels: dict[tuple[str, str, int | None], dict[str, Any]],
) -> dict[str, Any]:
    """Per-case scores and flags for one run (AB-8 to AB-15, AB-26 to AB-29, AB-37)."""

    cases: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    reads_needed: list[str] = []

    for case_id in case_ids:
        question = questions[case_id]
        result = run["results"].get(case_id)
        behaviour = expected_behaviour(question)
        label = find_label(labels, case_id, run["model"], run["run_no"])
        label_score = label.get("refusal_score") if label else None
        entry: dict[str, Any] = {
            "behaviour": behaviour,
            "group": group_of(question),
            "missing": is_missing(result),
            "accuracy": None,
            "citation": None,
            "refusal": None,
            "needs_read": False,
            "flags": [],
            "refused": None,
            "answer": "",
        }

        if entry["missing"]:
            missing.append(case_id)
            entry["refusal"] = 0
            entry["citation"] = 0 if behaviour in CITATION_TYPES else None
            entry["accuracy"] = 0 if question.get("expected_answer") else None
            cases[case_id] = entry
            continue

        metrics = result["metrics"]
        answer = result.get("model_answer") or ""
        refused = bool(metrics.get("refused"))
        cite_present = bool(metrics.get("citation_present"))
        cite_valid = metrics.get("citation_valid") is not False
        entry["refused"] = refused
        entry["answer"] = answer

        if question.get("expected_answer"):
            if not metrics.get("answer_returned", bool(answer.strip())):
                entry["accuracy"] = 0
            else:
                entry["accuracy"] = accuracy_score(result)

        if behaviour in CITATION_TYPES:
            entry["citation"] = citation_score(metrics)

        score, needs_read = refusal_score(
            behaviour, refused, cite_present, cite_valid, label_score
        )
        entry["refusal"] = score
        entry["needs_read"] = needs_read

        if needs_read:
            reads_needed.append(case_id)

        if metrics.get("citation_valid") is False:
            entry["flags"].append("AB-28")

        stated_amount = bool(AMOUNT_PATTERN.search(answer)) and not (
            cite_present and cite_valid
        )

        if behaviour in REFUSAL_TYPES and stated_amount:
            entry["flags"].append("AB-26")

        if behaviour == "declined" and score == 0:
            entry["flags"].append("AB-26")

        if question.get("question_type") == "fabricated_reference" and score == 0:
            entry["flags"].append("AB-27")

        cases[case_id] = entry

    return {"cases": cases, "missing": missing, "reads_needed": reads_needed}


def refusal_dimension(cases: dict[str, dict[str, Any]]) -> float | None:
    """AB-15: half the refusal-type mean, half the answer-type mean."""

    refusal_scores = [c["refusal"] for c in cases.values() if c["behaviour"] in REFUSAL_TYPES and c["refusal"] is not None]
    answer_scores = [c["refusal"] for c in cases.values() if c["behaviour"] in ANSWER_TYPES and c["refusal"] is not None]

    halves = [mean(scores) for scores in (refusal_scores, answer_scores) if scores]

    if not halves:
        return None

    return mean(halves)


def gate_results(scored: dict[str, Any], case_total: int) -> dict[str, Any]:
    """AB-26 to AB-29 for one run."""

    cases = scored["cases"]
    failing: dict[str, list[str]] = {gate: [] for gate in GATES}

    for case_id, entry in cases.items():
        if entry["missing"]:
            continue

        for flag in set(entry["flags"]):
            failing[flag].append(case_id)

    refusal_cases = {i: c for i, c in cases.items() if c["behaviour"] in REFUSAL_TYPES}
    missing_refusal = [i for i, c in refusal_cases.items() if c["missing"]]
    present_refusal = [c for c in refusal_cases.values() if not c["missing"]]

    recall = (
        sum(1 for c in present_refusal if (c["refusal"] or 0) > 0) / len(present_refusal)
        if present_refusal
        else None
    )

    refused = [c for c in cases.values() if not c["missing"] and c["refused"]]
    precision = (
        sum(1 for c in refused if c["behaviour"] in REFUSAL_TYPES) / len(refused)
        if refused
        else None
    )

    over_refusals = [
        i
        for i, c in cases.items()
        if not c["missing"] and c["behaviour"] == "answered" and c["refused"]
    ]

    status: dict[str, str] = {}
    status["AB-26"] = "fail" if failing["AB-26"] else "pass"
    status["AB-27"] = "fail" if failing["AB-27"] else "pass"
    status["AB-28"] = "fail" if failing["AB-28"] else "pass"

    recall_fail = recall is not None and recall < RECALL_GATE
    precision_fail = precision is not None and precision < PRECISION_GATE

    reasons: dict[str, str] = {}

    if recall_fail or precision_fail:
        status["AB-29"] = "fail"
        parts = []

        if recall_fail:
            parts.append(f"recall {recall:.2f}")

        if precision_fail:
            parts.append(f"precision {precision:.2f}")

        reasons["AB-29"] = ", ".join(parts)
        misses = [
            i
            for i, c in refusal_cases.items()
            if not c["missing"] and (c["refusal"] or 0) == 0
        ]
        failing["AB-29"] = sorted(set(misses + over_refusals))
    elif missing_refusal:
        status["AB-29"] = "unconfirmed"
    else:
        status["AB-29"] = "pass"

    limit = percent_missing_limit(case_total)
    not_evaluated = len(scored["missing"]) > limit

    return {
        "status": status,
        "failing": failing,
        "reasons": reasons,
        "recall": recall,
        "precision": precision,
        "missing_refusal": missing_refusal,
        "not_evaluated": not_evaluated,
        "missing_limit": limit,
    }


def latency_dimension(run: dict[str, Any], case_ids: list[str]) -> dict[str, Any]:
    """AB-17 and AB-18. Scored only when every ok result carries the attempt time."""

    ordered = [i for i in run["order"] if i in case_ids]
    ok = [run["results"][i] for i in ordered if not is_missing(run["results"].get(i))]
    warm = ok[COLD_REQUESTS:]

    attempt = [r[F_ATTEMPT_MS] / 1000 for r in warm if r.get(F_ATTEMPT_MS) is not None]
    raw = [
        r["generation_latency_ms"] / 1000
        for r in warm
        if r.get("generation_latency_ms") is not None
    ]

    measured = bool(ok) and all(r.get(F_ATTEMPT_MS) is not None for r in ok)
    source = attempt if measured else raw

    p50 = percentile(source, 50)
    p95 = percentile(source, 95)

    score = None

    if measured and p50 is not None and p95 is not None:
        score = mean(
            [
                latency_points(p50, P50_TARGET_S),
                latency_points(p95, P95_TARGET_S),
            ]
        )

    return {"measured": measured, "p50": p50, "p95": p95, "score": score, "samples": len(source)}


def latency_points(value: float, target: float) -> float:
    points = 100 * (LATENCY_FLOOR_S - value) / (LATENCY_FLOOR_S - target)

    return max(0.0, min(100.0, points))


def cost_dimension(
    run: dict[str, Any],
    case_ids: list[str],
    prices: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """AB-21 to AB-24. Needs usage tokens on every ok result and a recorded price."""

    ok = [run["results"][i] for i in case_ids if not is_missing(run["results"].get(i))]
    price = prices.get(run["model"])
    usage_ok = bool(ok) and all(
        r.get(F_PROMPT_TOKENS) is not None and r.get(F_COMPLETION_TOKENS) is not None
        for r in ok
    )

    if not usage_ok or price is None:
        return {"measured": False, "per_1000": None, "score": None}

    per_question = [
        r[F_PROMPT_TOKENS] * price["input_per_mtok"] / 1e6
        + r[F_COMPLETION_TOKENS] * price["output_per_mtok"] / 1e6
        for r in ok
    ]
    per_1000 = 1000 * mean(per_question)

    score = 0

    for limit, points in COST_BANDS:
        if per_1000 <= limit:
            score = points
            break

    return {"measured": True, "per_1000": per_1000, "score": score}


def composite(dimension_scores: dict[str, float | None], included: list[str]) -> float | None:
    total = sum(WEIGHTS[d] for d in included)

    if not included or total == 0:
        return None

    return sum(WEIGHTS[d] * dimension_scores[d] for d in included) / total


def spread(values: list[float]) -> tuple[float, float]:
    return mean(values), max(values) - min(values)


def analyse(
    runs: list[dict[str, Any]],
    questions: dict[str, dict[str, Any]],
    labels: dict[tuple[str, str, int | None], dict[str, Any]],
    prices: dict[str, dict[str, Any]],
    common_only: bool = False,
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    """Score every run and roll the runs up per model."""

    excluded = sorted(exclude or set())
    all_ids = [i for i in questions if i not in excluded]

    if common_only:
        shared = set.intersection(*(set(r["results"]) for r in runs)) if runs else set()
        case_ids = [i for i in all_ids if i in shared]
    else:
        case_ids = all_ids

    scored = {(r["model"], r["run_no"]): score_run(r, questions, case_ids, labels) for r in runs}

    judge_failed = set()
    any_judge = False

    for key, data in scored.items():
        for case_id, entry in data["cases"].items():
            if questions[case_id].get("expected_answer") and not entry["missing"]:
                if entry["accuracy"] is None:
                    judge_failed.add(case_id)
                else:
                    any_judge = True

    accuracy_ids = [
        i for i in case_ids if questions[i].get("expected_answer") and i not in judge_failed
    ]

    run_rows = []

    for run in runs:
        key = (run["model"], run["run_no"])
        data = scored[key]
        cases = data["cases"]

        accuracy = (
            mean(cases[i]["accuracy"] for i in accuracy_ids) if accuracy_ids and any_judge else None
        )
        cite_scores = [c["citation"] for c in cases.values() if c["citation"] is not None]
        citation = mean(cite_scores) if cite_scores else None
        refusal = refusal_dimension(cases)
        latency = latency_dimension(run, case_ids)
        cost = cost_dimension(run, case_ids, prices)

        run_rows.append(
            {
                "model": run["model"],
                "run_no": run["run_no"],
                "path": run["path"],
                "dimensions": {
                    "accuracy": accuracy,
                    "citation": citation,
                    "refusal": refusal,
                    "latency": latency["score"],
                    "cost": cost["score"],
                },
                "latency": latency,
                "cost": cost,
                "gates": gate_results(data, len(case_ids)),
                "missing": data["missing"],
                "reads_needed": data["reads_needed"],
            }
        )

    included = [
        d for d in DIMENSIONS if all(row["dimensions"][d] is not None for row in run_rows)
    ]

    for row in run_rows:
        row["composite"] = composite(row["dimensions"], included)

    models = []

    for model in dict.fromkeys(r["model"] for r in runs):
        rows = [r for r in run_rows if r["model"] == model]
        dims = {}

        for d in DIMENSIONS:
            values = [r["dimensions"][d] for r in rows if r["dimensions"][d] is not None]
            dims[d] = spread(values) if len(values) == len(rows) else None

        comp = [r["composite"] for r in rows if r["composite"] is not None]
        gate_status = "pass"
        failing_answers = 0

        for row in rows:
            for gate in GATES:
                state = row["gates"]["status"][gate]

                if state == "fail":
                    gate_status = "fail"
                    failing_answers += len(row["gates"]["failing"][gate])
                elif state == "unconfirmed" and gate_status != "fail":
                    gate_status = "unconfirmed"

        not_evaluated = any(r["gates"]["not_evaluated"] for r in rows)

        models.append(
            {
                "model": model,
                "runs": len(rows),
                "dimensions": dims,
                "composite": spread(comp) if comp and len(comp) == len(rows) else None,
                "gate_status": gate_status,
                "failing_answers": failing_answers,
                "not_evaluated": not_evaluated,
            }
        )

    return {
        "case_ids": case_ids,
        "accuracy_ids": accuracy_ids,
        "judge_excluded": sorted(judge_failed),
        "included": included,
        "dropped": [d for d in DIMENSIONS if d not in included],
        "runs": run_rows,
        "models": models,
        "scored": scored,
        "common_only": common_only,
        "excluded": excluded,
    }


def rank_models(models: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    """AB-46 ordering; the flag is True when no model passes every gate (AB-32)."""

    evaluated = [m for m in models if not m["not_evaluated"] and m["composite"] is not None]
    passing = [m for m in evaluated if m["gate_status"] == "pass"]
    none_pass = not passing

    if none_pass:
        ordered = sorted(
            evaluated,
            key=lambda m: (m["failing_answers"], -m["composite"][0]),
        )
    else:
        rest = [m for m in evaluated if m["gate_status"] != "pass"]
        ordered = sorted(passing, key=lambda m: -m["composite"][0]) + sorted(
            rest, key=lambda m: -m["composite"][0]
        )

    return ordered, none_pass


def mean_case_scores(
    analysis: dict[str, Any], model: str, dimension: str
) -> dict[str, float]:
    """Per-case score averaged over a model's runs."""

    buckets: dict[str, list[float]] = defaultdict(list)

    for (m, _), data in analysis["scored"].items():
        if m != model:
            continue

        for case_id, entry in data["cases"].items():
            if dimension == "accuracy" and case_id not in analysis["accuracy_ids"]:
                continue

            if entry[dimension] is not None:
                buckets[case_id].append(entry[dimension])

    return {i: mean(v) for i, v in buckets.items()}


def net_margin(analysis: dict[str, Any], first: str, second: str, dimension: str) -> int:
    """AB-43: cases where `first` scores higher minus cases where it scores lower."""

    a = mean_case_scores(analysis, first, dimension)
    b = mean_case_scores(analysis, second, dimension)

    higher = sum(1 for i in a if i in b and a[i] > b[i])
    lower = sum(1 for i in a if i in b and a[i] < b[i])

    return higher - lower


def changed_cases(analysis: dict[str, Any], model: str) -> int | None:
    """AB-45: cases whose score differs between a model's runs."""

    runs = [data for (m, _), data in analysis["scored"].items() if m == model]

    if len(runs) < 2:
        return None

    count = 0

    for case_id in analysis["case_ids"]:
        values = []

        for data in runs:
            entry = data["cases"][case_id]
            key = "accuracy" if case_id in analysis["accuracy_ids"] else None
            values.append(
                (
                    entry["refusal"],
                    entry["citation"],
                    entry[key] if key else None,
                )
            )

        if len(set(values)) > 1:
            count += 1

    return count


def decide(analysis: dict[str, Any]) -> dict[str, Any]:
    """AB-46 to AB-50 for the two leading models."""

    ordered, none_pass = rank_models(analysis["models"])

    if len(ordered) < 2:
        return {"ordered": ordered, "none_pass": none_pass, "trace": [], "verdict": "Fewer than two evaluated models."}

    first, second = ordered[0], ordered[1]
    gap = first["composite"][0] - second["composite"][0]
    widest = max(first["composite"][1], second["composite"][1])
    close = gap < CLOSE_COMPOSITE_GAP or gap < widest

    trace: list[dict[str, Any]] = []

    if none_pass:
        verdict = (
            "No candidate passes every gate. On this evidence none is fit for client use (AB-32). "
            "The order above is provisional."
        )
        return {"ordered": ordered, "none_pass": True, "trace": trace, "verdict": verdict, "gap": gap, "close": close}

    if not close:
        verdict = f"{first['model']} wins on composite (gap {gap:.1f}, AB-48)."
        return {"ordered": ordered, "none_pass": False, "trace": trace, "verdict": verdict, "gap": gap, "close": close}

    a, b = first["model"], second["model"]

    for name, dimension in (("Refusal behaviour", "refusal"), ("Citation support", "citation")):
        margin = net_margin(analysis, a, b, dimension)
        real = abs(margin) >= REAL_MARGIN
        trace.append(
            {
                "rule": name,
                "result": f"net margin {margin:+d} for {a}",
                "real": real,
                "winner": a if margin > 0 else b if margin < 0 else None,
            }
        )

        if real:
            winner = a if margin > 0 else b
            return {
                "ordered": ordered,
                "none_pass": False,
                "trace": trace,
                "verdict": f"Composites are close (gap {gap:.1f}). {winner} wins on {name.lower()} (AB-49).",
                "gap": gap,
                "close": close,
            }

    trace.append(
        {
            "rule": "Accuracy",
            "result": "needs an analyst read of the cases where judge correctness differs by 2 or more (AB-49 rule 3)",
            "real": False,
            "winner": None,
        }
    )

    changes = {m: changed_cases(analysis, m) for m in (a, b)}

    if None not in changes.values():
        difference = changes[a] - changes[b]
        real = abs(difference) >= REAL_MARGIN
        trace.append(
            {
                "rule": "Consistency",
                "result": f"cases changing between runs: {a} {changes[a]}, {b} {changes[b]}",
                "real": real,
                "winner": b if difference > 0 else a if difference < 0 else None,
            }
        )

        if real:
            winner = b if difference > 0 else a
            return {
                "ordered": ordered,
                "none_pass": False,
                "trace": trace,
                "verdict": f"Composites are close (gap {gap:.1f}). {winner} wins on consistency (AB-49), subject to the accuracy read.",
                "gap": gap,
                "close": close,
            }
    else:
        trace.append(
            {"rule": "Consistency", "result": "needs 2 or more runs per model", "real": False, "winner": None}
        )

    rows = {
        m: [r for r in analysis["runs"] if r["model"] == m] for m in (a, b)
    }
    lat = {
        m: (
            mean(r["latency"]["p50"] for r in rows[m] if r["latency"]["p50"] is not None),
            mean(r["latency"]["p95"] for r in rows[m] if r["latency"]["p95"] is not None),
        )
        if all(r["latency"]["measured"] for r in rows[m])
        else None
        for m in (a, b)
    }

    if None in lat.values():
        trace.append(
            {"rule": "Latency", "result": "not measured to the AB-17 method (no successful-attempt time)", "real": False, "winner": None}
        )
    else:
        a_faster = lat[a][0] <= (1 - REAL_LATENCY_DROP) * lat[b][0] and lat[a][1] <= (1 - REAL_LATENCY_DROP) * lat[b][1]
        b_faster = lat[b][0] <= (1 - REAL_LATENCY_DROP) * lat[a][0] and lat[b][1] <= (1 - REAL_LATENCY_DROP) * lat[a][1]
        winner = a if a_faster else b if b_faster else None
        trace.append(
            {
                "rule": "Latency",
                "result": f"p50/p95 {a} {lat[a][0]:.1f}/{lat[a][1]:.1f}s, {b} {lat[b][0]:.1f}/{lat[b][1]:.1f}s",
                "real": winner is not None,
                "winner": winner,
            }
        )

        if winner:
            return {
                "ordered": ordered,
                "none_pass": False,
                "trace": trace,
                "verdict": f"Composites are close (gap {gap:.1f}). {winner} wins on latency (AB-49), subject to the accuracy read.",
                "gap": gap,
                "close": close,
            }

    cost = {
        m: [r["cost"]["score"] for r in rows[m]] for m in (a, b)
    }

    if any(s is None for scores in cost.values() for s in scores):
        trace.append({"rule": "Cost band", "result": "not measured", "real": False, "winner": None})
    else:
        band = {m: mean(cost[m]) for m in (a, b)}
        winner = a if band[a] > band[b] else b if band[b] > band[a] else None
        trace.append(
            {
                "rule": "Cost band",
                "result": f"band score {a} {band[a]:.0f}, {b} {band[b]:.0f}",
                "real": winner is not None,
                "winner": winner,
            }
        )

        if winner:
            return {
                "ordered": ordered,
                "none_pass": False,
                "trace": trace,
                "verdict": f"Composites are close (gap {gap:.1f}). {winner} wins on cost band (AB-49).",
                "gap": gap,
                "close": close,
            }

    verdict = (
        f"Composites are close (gap {gap:.1f}) and no rule in AB-49 shows a real difference that is "
        "free of a manual read. Treat as no clear winner on this benchmark (AB-50)."
    )

    return {"ordered": ordered, "none_pass": False, "trace": trace, "verdict": verdict, "gap": gap, "close": close}


def fmt(value: float | None, digits: int = 1) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def fmt_spread(pair: tuple[float, float] | None) -> str:
    if pair is None:
        return "n/a"

    mean_value, width = pair
    return f"{mean_value:.1f}" if width == 0 else f"{mean_value:.1f} ({width:.1f})"


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]

    return lines


def group_rows(
    analysis: dict[str, Any],
    questions: dict[str, dict[str, Any]],
    key_fn,
    keys: list[str],
) -> list[list[str]]:
    """AB-41 and AB-42: per group and model; small groups show counts."""

    rows = []

    for key in keys:
        ids = [i for i in analysis["case_ids"] if key_fn(questions[i]) == key]

        if not ids:
            continue

        for model in dict.fromkeys(m["model"] for m in analysis["models"]):
            cells = [key, model, str(len(ids))]

            for dimension in ("accuracy", "citation", "refusal"):
                applicable = [
                    i
                    for i in ids
                    if (dimension != "accuracy" or i in analysis["accuracy_ids"])
                ]
                scores = mean_case_scores(analysis, model, dimension)
                values = [scores[i] for i in applicable if i in scores]

                if not values:
                    cells.append("-")
                elif len(ids) < 10:
                    full = sum(1 for v in values if v == 100)
                    cells.append(f"{full} of {len(values)} at 100")
                else:
                    cells.append(f"{mean(values):.1f}")

            failures = 0

            for (m, _), data in analysis["scored"].items():
                if m == model:
                    failures += sum(1 for i in ids if data["cases"][i]["flags"])

            cells.append(str(failures))
            rows.append(cells)

    return rows


def build_report(
    analysis: dict[str, Any],
    questions: dict[str, dict[str, Any]],
    questions_path: str | Path,
    runs: list[dict[str, Any]],
    title: str,
) -> str:
    decision = decide(analysis)
    ordered = decision["ordered"]
    lines = [f"# {title}", ""]

    lines += [
        "Computed by `scripts/ab_analysis.py` under `docs/MODEL-AB-SCORING.md`. Every number below comes from the result files and the questions file listed in the settings block.",
        "",
    ]

    scope = (
        f"{len(analysis['case_ids'])} cases common to every run file (`--common-cases`). This is NOT an AB-conformant run set (AB-1, AB-4, AB-38): it is the interim view the evidence allows."
        if analysis["common_only"]
        else f"{len(analysis['case_ids'])} cases in the questions file."
    )

    lines += ["## 1. Settings (AB-1, AB-2)", "", f"- Questions file: `{questions_path}`, sha256 prefix `{file_hash(questions_path)}`.", f"- Scope: {scope}"]
    lines += [
        f"- Removed for every model because the cause is not the candidate (AB-39): {', '.join(analysis['excluded']) or 'none'}.",
        f"- Dimensions scored: {', '.join(analysis['included']) or 'none'}. Dropped for every model under AB-35: {', '.join(analysis['dropped']) or 'none'}.",
        "",
    ]

    setting_rows = []

    for run in runs:
        results = list(run["results"].values())
        first = results[0]
        judges = sorted({(r.get("judge") or {}).get("judge_model") for r in results if r.get("judge")} - {None})
        stamps = sorted(r["created_at"] for r in results if r.get("created_at"))
        temperature = sorted({str(r[F_TEMPERATURE]) for r in results if r.get(F_TEMPERATURE) is not None})
        answered_by = sorted({r[F_ANSWERED_BY] for r in results if r.get(F_ANSWERED_BY)})
        mismatched = [
            i
            for i, r in run["results"].items()
            if i in questions and r.get("question") != questions[i]["question"]
        ]

        setting_rows.append(
            [
                f"`{run['model']}`",
                str(run["run_no"]),
                f"`{Path(run['path']).name}`",
                str(len(results)),
                f"{first.get('retrieval_strategy', 'n/a')} / {first.get('top_k', 'n/a')}",
                ", ".join(temperature) or "not recorded",
                ", ".join(answered_by) or "not recorded",
                ", ".join(f"`{j}`" for j in judges) or "none",
                (stamps[0][:10] + " to " + stamps[-1][:10]) if stamps else "n/a",
                ", ".join(mismatched) or "none",
            ]
        )

    lines += table(
        ["Model", "Run", "File", "Records", "Retrieval / top k", "Temperature", "Answering model", "Judge", "Dates", "Question text differs from file"],
        setting_rows,
    )

    lines += ["", "## 2. Completeness (AB-37 to AB-40)", ""]
    complete_rows = []

    for row in analysis["runs"]:
        gates = row["gates"]
        complete_rows.append(
            [
                f"`{row['model']}`",
                str(row["run_no"]),
                f"{len(analysis['case_ids']) - len(row['missing'])} of {len(analysis['case_ids'])}",
                ", ".join(row["missing"][:8]) + (" ..." if len(row["missing"]) > 8 else "") or "none",
                str(gates["missing_limit"]),
                "not evaluated" if gates["not_evaluated"] else "evaluated",
            ]
        )

    lines += table(["Model", "Run", "Answered", "Missing ids", "Allowed missing", "Status"], complete_rows)
    lines += ["", f"Judge failures removed from accuracy for every model (AB-9): {', '.join(analysis['judge_excluded']) or 'none'}.", ""]

    lines += ["## 3. Retrieval check (AB-6)", ""]
    differing = []

    for case_id in analysis["case_ids"]:
        seen = {
            tuple(r["results"][case_id].get("retrieved_chunk_ids") or [])
            for r in runs
            if case_id in r["results"] and not is_missing(r["results"][case_id])
        }

        if len(seen) > 1:
            differing.append(case_id)

    lines.append(
        "Retrieved chunk ids are identical across every run for every case."
        if not differing
        else f"Retrieved chunk ids differ between runs for {len(differing)} cases: {', '.join(differing)}. Investigate before comparing scores, because AB-1 did not hold."
    )

    lines += ["", "## 4. Gates (AB-26 to AB-29)", ""]
    gate_rows = []

    for row in analysis["runs"]:
        gates = row["gates"]
        cells = [f"`{row['model']}`", str(row["run_no"])]

        for gate in GATES:
            state = gates["status"][gate]
            ids = ", ".join(gates["failing"][gate])
            reason = gates["reasons"].get(gate)
            label = f"{state} ({reason})" if reason else state
            cells.append(label if not ids else f"{label}: {ids}")

        cells.append(f"{fmt(gates['recall'], 2)} / {fmt(gates['precision'], 2)}")
        gate_rows.append(cells)

    lines += table(["Model", "Run", "AB-26 unsafe", "AB-27 fabricated", "AB-28 citation resolution", "AB-29 refusal", "Recall / precision"], gate_rows)
    lines += ["", "AB-26 and AB-27 are screening flags from code (AB-16). AB-30 requires an analyst to read an answer before a flag disqualifies a model.", ""]

    lines += ["## 5. Dimension scores and composite (AB-33 to AB-36)", ""]
    score_rows = []

    for model in analysis["models"]:
        dims = model["dimensions"]
        score_rows.append(
            [f"`{model['model']}`", str(model["runs"])]
            + [fmt_spread(dims[d]) for d in DIMENSIONS]
            + [fmt_spread(model["composite"]), model["gate_status"] if not model["not_evaluated"] else "not evaluated"]
        )

    lines += table(
        ["Model", "Runs", "Accuracy", "Citation", "Refusal", "Latency", "Cost", "Composite", "Gates"],
        score_rows,
    )
    lines += ["", "Cells show the mean over runs, with the range (highest minus lowest) in brackets when there is more than one run. `n/a` means not measured (AB-24, AB-35).", ""]

    latency_rows = []

    for row in analysis["runs"]:
        latency = row["latency"]
        latency_rows.append(
            [
                f"`{row['model']}`",
                str(row["run_no"]),
                "yes" if latency["measured"] else "no",
                fmt(latency["p50"]),
                fmt(latency["p95"]),
                str(latency["samples"]),
                fmt(row["cost"]["per_1000"], 2),
            ]
        )

    lines += table(
        ["Model", "Run", "Successful-attempt time recorded", "Generation p50 (s)", "Generation p95 (s)", "Samples", "Cost per 1,000 questions"],
        latency_rows,
    )
    lines += ["", "Where the attempt time is not recorded, p50 and p95 are the harness `generation_latency_ms`, which includes retry and rate-limit waits. They are shown for context and are not scored (AB-17, LT-20).", ""]

    lines += ["## 6. Groups (section 8, AB-41, AB-42)", ""]
    header = ["Group", "Model", "Cases", "Accuracy", "Citation", "Refusal", "Gate-flagged answers"]
    lines += table(header, group_rows(analysis, questions, group_of, GROUP_ORDER))

    behaviours = sorted({expected_behaviour(questions[i]) for i in analysis["case_ids"]})
    lines += ["", "By expected behaviour:", ""]
    lines += table(["Expected behaviour"] + header[1:], group_rows(analysis, questions, expected_behaviour, behaviours))

    types = sorted({questions[i].get("question_type") or "unclassified" for i in analysis["case_ids"]})
    lines += ["", "By question type:", ""]
    lines += table(
        ["Question type"] + header[1:],
        group_rows(analysis, questions, lambda q: q.get("question_type") or "unclassified", types),
    )

    year_ids = [i for i in analysis["case_ids"] if group_of(questions[i]) == "Income year" and questions[i].get("income_year")]
    lines += ["", "Income-year check (reported, not scored): answers that state the case's `income_year`.", ""]
    year_rows = []

    for model in dict.fromkeys(r["model"] for r in runs) if year_ids else []:
        for run in [r for r in runs if r["model"] == model]:
            states = [
                states_income_year(run["results"][i].get("model_answer") or "", questions[i]["income_year"])
                for i in year_ids
                if i in run["results"] and not is_missing(run["results"][i])
            ]
            year_rows.append([f"`{model}`", str(run["run_no"]), f"{sum(states)} of {len(states)}"])

    lines += table(["Model", "Run", "States the income year"], year_rows) if year_rows else ["No income-year cases in scope."]

    lines += ["", "## 7. Ranking and decision (AB-32, AB-43 to AB-50)", ""]
    rank_rows = []

    for position, model in enumerate(ordered, start=1):
        rank_rows.append(
            [
                str(position),
                f"`{model['model']}`",
                fmt_spread(model["composite"]),
                model["gate_status"],
                str(model["failing_answers"]),
            ]
        )

    unranked = [m for m in analysis["models"] if m not in ordered]

    for model in unranked:
        rank_rows.append(["-", f"`{model['model']}`", fmt_spread(model["composite"]), "not evaluated" if model["not_evaluated"] else model["gate_status"], str(model["failing_answers"])])

    lines += table(["Order", "Model", "Composite", "Gates", "Failing answers across runs"], rank_rows)
    lines += ["", f"**{decision['verdict']}**", ""]

    if decision["trace"]:
        lines += table(
            ["AB-49 rule", "Result", "Real difference", "Favours"],
            [[t["rule"], t["result"], "yes" if t["real"] else "no", f"`{t['winner']}`" if t["winner"] else "-"] for t in decision["trace"]],
        )
        lines.append("")

    if len(ordered) >= 2:
        a, b = ordered[0]["model"], ordered[1]["model"]
        margin_rows = [
            [d.title(), f"{net_margin(analysis, a, b, d):+d}"]
            for d in ("accuracy", "citation", "refusal")
        ]
        lines += [f"Net case margin of `{a}` over `{b}` (AB-43, real at {REAL_MARGIN} or more):", ""]
        lines += table(["Dimension", "Net margin"], margin_rows)
        lines.append("")

    reads = sorted({(r["model"], r["run_no"], i) for r in analysis["runs"] for i in r["reads_needed"]})
    lines += ["## 8. Cases needing an analyst read (AB-16)", ""]

    if reads:
        grouped: dict[tuple[str, int], list[str]] = defaultdict(list)

        for model, run_no, case_id in reads:
            grouped[(model, run_no)].append(case_id)

        lines += table(
            ["Model", "Run", "Cases scored by the screening default"],
            [[f"`{m}`", str(n), ", ".join(ids)] for (m, n), ids in grouped.items()],
        )
    else:
        lines.append("None.")

    judge_gaps = []

    for case_id in analysis["accuracy_ids"]:
        values = [
            data["cases"][case_id]["accuracy"]
            for data in analysis["scored"].values()
            if data["cases"][case_id]["accuracy"] is not None
        ]

        if values and max(values) - min(values) >= 50:
            judge_gaps.append(case_id)

    lines += ["", f"Cases where judge correctness differs by 2 or more between runs or models (AB-49 rule 3 read): {', '.join(judge_gaps) or 'none'}.", ""]

    comma = sorted(
        {
            (r["model"], r["run_no"], i)
            for r in runs
            for i, res in r["results"].items()
            if COMMA_MARKER_PATTERN.search(res.get("model_answer") or "")
        }
    )
    lines.append(
        f"Answers using comma-list or range citations such as `[1, 2]`, which the harness does not count (CB-8): {len(comma)}."
        + (" " + ", ".join(f"{m} run {n} {i}" for m, n, i in comma[:12]) if comma else "")
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Score model runs under docs/MODEL-AB-SCORING.md.")
    parser.add_argument("results", nargs="+", help="Result JSONL files, one per model run. Runs of one model are numbered in the order given.")
    parser.add_argument("--questions", default="benchmarks/questions.jsonl")
    parser.add_argument("--labels", help="JSONL of analyst reads (AB-16): {id, model, run (optional), refusal_score, reason, date}.")
    parser.add_argument("--prices", help="JSON: {model: {input_per_mtok, output_per_mtok, source_url, date_read}}.")
    parser.add_argument("--common-cases", action="store_true", help="Score only the cases present in every run file (interim view, not AB-conformant).")
    parser.add_argument("--exclude", default="", help="Comma-separated case ids removed for every model (AB-39), for failures the candidate did not cause.")
    parser.add_argument("--output", default="benchmarks/reports/ab_analysis.md")
    parser.add_argument("--title", default="Model A/B analysis")
    args = parser.parse_args()

    questions = {q["id"]: q for q in load_jsonl(args.questions)}
    runs = load_runs(args.results)
    labels = load_labels(args.labels)
    prices = json.loads(Path(args.prices).read_text(encoding="utf-8")) if args.prices else {}

    exclude = {i.strip() for i in args.exclude.split(",") if i.strip()}
    analysis = analyse(runs, questions, labels, prices, common_only=args.common_cases, exclude=exclude)
    report = build_report(analysis, questions, args.questions, runs, args.title)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")

    print(f"Report written to: {output}")


if __name__ == "__main__":
    main()
