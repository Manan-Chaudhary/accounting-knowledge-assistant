import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from app.evaluation import harness


def load_results(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None

    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))

    return ordered[rank - 1]


def rate(results: list[dict[str, Any]], metric: str) -> float | None:
    """Share of True values for a boolean metric, ignoring cases where it is None."""

    values = [
        r["metrics"].get(metric)
        for r in results
        if r["metrics"].get(metric) is not None
    ]

    if not values:
        return None

    return sum(bool(v) for v in values) / len(values)


def average(results: list[dict[str, Any]], metric: str) -> float | None:
    values = [
        r["metrics"][metric]
        for r in results
        if r["metrics"].get(metric) is not None
    ]

    return mean(values) if values else None


def judge_average(results: list[dict[str, Any]], field: str) -> float | None:
    values = [
        r["judge"][field]
        for r in results
        if r.get("judge") and isinstance(r["judge"].get(field), (int, float))
    ]

    return mean(values) if values else None


def refusal_scores(results: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    """Refusal recall and precision, as defined in docs/EVALUATION.md section 4."""

    answered = [r for r in results if r["metrics"].get("provider_available", True)]
    must = [r for r in answered if r.get("must_refuse")]
    refused = [r for r in answered if r["metrics"].get("refused")]

    recall = (
        sum(bool(r["metrics"].get("refused")) for r in must) / len(must)
        if must else None
    )
    precision = (
        sum(bool(r.get("must_refuse")) for r in refused) / len(refused)
        if refused else None
    )

    return recall, precision


def summarise(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in results if r.get("status", "ok") == "ok"]
    latencies = [r["latency_ms"] for r in ok if r.get("latency_ms") is not None]
    recall, precision = refusal_scores(results)

    return {
        "cases": len(results),
        "provider_failures": len(results) - len(ok),
        "answer_returned": rate(results, "answer_returned"),
        "source_hit": rate(ok, "expected_source_hit"),
        "top1_hit": rate(ok, "top1_source_hit"),
        "recall_at_k": average(ok, "recall_at_k"),
        "mrr": average(ok, "reciprocal_rank"),
        "citation_present": rate([r for r in ok if not r.get("must_refuse")], "citation_present"),
        "citation_valid": rate(ok, "citation_valid"),
        "citation_format_standard": rate(ok, "citation_format_standard"),
        "refusal_correct": rate(ok, "refusal_correct"),
        "refusal_recall": recall,
        "refusal_precision": precision,
        "judge_correctness": judge_average(ok, "correctness"),
        "judge_faithfulness": judge_average(ok, "faithfulness"),
        "p50_latency_ms": percentile(latencies, 50),
        "p95_latency_ms": percentile(latencies, 95),
    }


def case_failures(result: dict[str, Any]) -> list[str]:
    if result.get("status", "ok") != "ok":
        return [result.get("status", "failed")]

    metrics = result["metrics"]
    failures = []

    if metrics.get("expected_source_hit") is False:
        failures.append("expected source not retrieved")

    if metrics.get("citation_valid") is False:
        failures.append(f"invalid citations {metrics.get('invalid_citations')}")

    if metrics.get("citation_format_standard") is False:
        failures.append("non-standard citation format")

    if not result.get("must_refuse") and not metrics.get("citation_present"):
        failures.append("no citation")

    if metrics.get("refusal_correct") is False:
        failures.append("missed refusal" if result.get("must_refuse") else "over-refusal")

    judge = result.get("judge") or {}

    if isinstance(judge.get("correctness"), (int, float)) and judge["correctness"] <= 2:
        failures.append(f"judge correctness {judge['correctness']}/5")

    return failures


def fmt(value: Any, kind: str = "pct") -> str:
    if value is None:
        return "n/a"

    if kind == "pct":
        return f"{value * 100:.0f}%"

    if kind == "ms":
        return f"{value / 1000:.1f}s"

    if kind == "score":
        return f"{value:.2f}"

    return str(value)


SUMMARY_COLUMNS = [
    ("Cases", "cases", "raw"),
    ("Provider failures", "provider_failures", "raw"),
    ("Source hit", "source_hit", "pct"),
    ("Top-1 hit", "top1_hit", "pct"),
    ("Recall@k", "recall_at_k", "score"),
    ("MRR", "mrr", "score"),
    ("Citation present (answerable cases)", "citation_present", "pct"),
    ("Citation valid", "citation_valid", "pct"),
    ("Citation format [n]", "citation_format_standard", "pct"),
    ("Refusal correct", "refusal_correct", "pct"),
    ("Refusal recall", "refusal_recall", "pct"),
    ("Refusal precision", "refusal_precision", "pct"),
    ("Judge correctness (1-5)", "judge_correctness", "score"),
    ("Judge faithfulness (1-5)", "judge_faithfulness", "score"),
    ("P50 latency", "p50_latency_ms", "ms"),
    ("P95 latency", "p95_latency_ms", "ms"),
]


def build_report(runs: dict[str, list[dict[str, Any]]], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `scripts/evaluation_report.py`.",
        "",
        "Metric definitions follow `docs/EVALUATION.md` section 4. Rates exclude cases where a metric does not apply "
        "(for example, source hit on must-refuse cases with no expected source).",
        "",
        "## Model comparison",
        "",
    ]

    models = list(runs)
    summaries = {model: summarise(results) for model, results in runs.items()}

    lines.append("| Metric | " + " | ".join(f"`{m}`" for m in models) + " |")
    lines.append("|---|" + "---|" * len(models))

    for label, key, kind in SUMMARY_COLUMNS:
        lines.append(
            f"| {label} | "
            + " | ".join(fmt(summaries[m][key], kind) for m in models)
            + " |"
        )

    lines += ["", "## Per-class results", ""]
    lines.append("| Class | Model | Cases | Source hit | Citation valid | Refusal correct | Judge correctness |")
    lines.append("|---|---|---|---|---|---|---|")

    for model, results in runs.items():
        by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for r in results:
            by_class[r.get("class") or "unclassified"].append(r)

        for cls in sorted(by_class):
            s = summarise(by_class[cls])
            lines.append(
                f"| {cls} | `{model}` | {s['cases']} | {fmt(s['source_hit'])} | "
                f"{fmt(s['citation_valid'])} | {fmt(s['refusal_correct'])} | "
                f"{fmt(s['judge_correctness'], 'score')} |"
            )

    lines += ["", "## Failures", ""]

    any_failure = False

    for model, results in runs.items():
        for r in results:
            failures = case_failures(r)

            if not failures:
                continue

            if not any_failure:
                lines.append("| Case | Model | Failed on | Retrieved files |")
                lines.append("|---|---|---|---|")
                any_failure = True

            files = ", ".join(dict.fromkeys(r.get("retrieved_files") or [])) or "none"
            lines.append(f"| {r['id']} | `{model}` | {'; '.join(failures)} | {files} |")

    if not any_failure:
        lines.append("No failed cases.")

    lines += ["", "## Case results", ""]
    lines.append("| Case | Class | Question | " + " | ".join(f"`{m}`" for m in models) + " |")
    lines.append("|---|---|---|" + "---|" * len(models))

    by_id: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    order: list[str] = []

    for model, results in runs.items():
        for r in results:
            if r["id"] not in by_id:
                order.append(r["id"])
            by_id[r["id"]][model] = r

    for case_id in order:
        first = next(iter(by_id[case_id].values()))
        cells = []

        for model in models:
            r = by_id[case_id].get(model)
            cells.append("n/a" if r is None else ("pass" if not case_failures(r) else "fail"))

        question = first["question"].replace("|", "/")
        lines.append(f"| {case_id} | {first.get('class') or ''} | {question} | " + " | ".join(cells) + " |")

    return "\n".join(lines) + "\n"


def write_report(
    result_paths: list[str | Path],
    output_path: str | Path,
    title: str,
    rescore: bool = False,
) -> Path:
    runs: dict[str, list[dict[str, Any]]] = {}

    for path in result_paths:
        results = load_results(path)

        if rescore:
            results = [harness.rescore(r) for r in results]
            Path(path).write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results),
                encoding="utf-8",
            )

        if not results:
            continue

        model = results[0].get("model_name") or Path(path).stem
        runs[model] = results

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_report(runs, title), encoding="utf-8")

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Build a markdown evaluation report from one or more result files."
    )

    parser.add_argument("results", nargs="+", help="Result JSONL files, one per model run.")
    parser.add_argument("--output", default="benchmarks/reports/evaluation_report.md")
    parser.add_argument("--title", default="Evaluation report")
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="Recompute deterministic metrics from the saved answers and update the result files first.",
    )

    args = parser.parse_args()

    output = write_report(args.results, args.output, args.title, rescore=args.rescore)

    print(f"Report written to: {output}")


if __name__ == "__main__":
    main()
