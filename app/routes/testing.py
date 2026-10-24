from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth.session import session_user_payload
from app.evaluation.harness import (
    DEFAULT_MODEL,
    DEFAULT_RETRIEVAL_STRATEGY,
    DEFAULT_TOP_K,
    RETRIEVAL_STRATEGIES,
    load_cases,
)
from scripts.evaluation_report import case_failures, load_results, summarise

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/testing", tags=["testing"])

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = Path(tempfile.gettempdir()) / "accounting-knowledge-assistant-eval-runs"
RUN_DIR.mkdir(parents=True, exist_ok=True)

TEST_SETS: dict[str, dict[str, str]] = {
    "core-mvp": {
        "label": "Core MVP Benchmark",
        "path": "benchmarks/questions.jsonl",
    },
}

# Keep this list aligned with litellm/config.yaml.
MODEL_OPTIONS = [
    {"id": "gemini-3-8-flash", "label": "Gemini 3.8 Flash"},
    {"id": "groq-gpt-oss-120b", "label": "Groq GPT-OSS 120B"},
    {"id": "openrouter-free", "label": "OpenRouter Free"},
    {"id": "free-fallback", "label": "Free Fallback"},
]
MODEL_IDS = {item["id"] for item in MODEL_OPTIONS}


def _default_model() -> str:
    """Map the harness default to a configured LiteLLM proxy alias."""

    if DEFAULT_MODEL in MODEL_IDS:
        return DEFAULT_MODEL

    if DEFAULT_MODEL == "gemini-3.8-flash":
        return "gemini-3-8-flash"

    return MODEL_OPTIONS[0]["id"]


TERMINAL_STATUSES = {"completed", "failed", "interrupted"}

_runs: dict[str, dict[str, Any]] = {}
_runs_lock = threading.Lock()
_active_run_id: str | None = None


class StartRunRequest(BaseModel):
    test_set: str = "core-mvp"
    model: str = Field(default_factory=_default_model)
    use_judge: bool = False
    judge_model: str | None = None
    retrieval_strategy: str = DEFAULT_RETRIEVAL_STRATEGY
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=20)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_team(request: Request) -> None:
    payload = session_user_payload(request)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    if payload.get("role") != "team":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team access required.",
        )


def _test_set_path(test_set_id: str) -> Path:
    item = TEST_SETS.get(test_set_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unknown evaluation test set.",
        )

    path = (REPO_ROOT / item["path"]).resolve()

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The configured evaluation test set is unavailable.",
        )

    return path


def _validate_request(body: StartRunRequest) -> tuple[Path, str | None]:
    questions_path = _test_set_path(body.test_set)

    if body.model not in MODEL_IDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unknown evaluation model.",
        )

    strategy = body.retrieval_strategy.strip().lower()
    if strategy not in RETRIEVAL_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unknown retrieval strategy.",
        )

    judge_model: str | None = None
    if body.use_judge:
        judge_model = body.judge_model or body.model
        if judge_model not in MODEL_IDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Unknown judge model.",
            )

    load_cases(questions_path)

    return questions_path, judge_model


def _build_command(
    *,
    questions_path: Path,
    output_path: Path,
    model: str,
    top_k: int,
    retrieval_strategy: str,
    judge_model: str | None,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "scripts.run_evaluation",
        "--questions",
        str(questions_path),
        "--output",
        str(output_path),
        "--model",
        model,
        "--top-k",
        str(top_k),
        "--strategy",
        retrieval_strategy,
    ]

    if judge_model:
        command.extend(["--judge", judge_model])

    return command


def _spawn_process(
    *,
    command: list[str],
    log_path: Path,
) -> tuple[subprocess.Popen[str], Any]:
    log_file = log_path.open("w", encoding="utf-8")

    try:
        process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception:
        log_file.close()
        raise

    return process, log_file


def _read_results(output_path: Path) -> list[dict[str, Any]]:
    if not output_path.exists():
        return []

    try:
        return load_results(output_path)
    except (OSError, ValueError):
        logger.exception("evaluation_progress_read_failed path=%s", output_path)
        return []


def _gate_min(value: float | None, threshold: float) -> str:
    if value is None:
        return "info"
    return "pass" if value >= threshold else "fail"


def _gate_max(value: float | None, threshold: float) -> str:
    if value is None:
        return "info"
    return "pass" if value <= threshold else "fail"


def _format_percent(value: float | None) -> str:
    return "Not available" if value is None else f"{value * 100:.0f}%"


def _format_score(value: float | None) -> str:
    return "Not available" if value is None else f"{value:.2f}"


def _format_judge(value: float | None) -> str:
    return "Not run" if value is None else f"{value:.2f} / 5"


def _format_latency(value: float | None) -> str:
    return "Not available" if value is None else f"{value / 1000:.1f}s"


def _build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarise(results)

    passed_cases = 0
    failed_cases = 0
    for result in results:
        if case_failures(result):
            failed_cases += 1
        else:
            passed_cases += 1

    metric_cards = [
        {
            "key": "recall_at_k",
            "label": "Recall @ K",
            "display": _format_percent(summary["recall_at_k"]),
            "gate": "≥ 95%",
            "outcome": _gate_min(summary["recall_at_k"], 0.95),
        },
        {
            "key": "mrr",
            "label": "MRR",
            "display": _format_score(summary["mrr"]),
            "gate": "Report only",
            "outcome": "info",
        },
        {
            "key": "citation_valid",
            "label": "Citation valid",
            "display": _format_percent(summary["citation_valid"]),
            "gate": "= 100%",
            "outcome": _gate_min(summary["citation_valid"], 1.0),
        },
        {
            "key": "refusal_recall",
            "label": "Refusal recall",
            "display": _format_percent(summary["refusal_recall"]),
            "gate": "≥ 95%",
            "outcome": _gate_min(summary["refusal_recall"], 0.95),
        },
        {
            "key": "refusal_precision",
            "label": "Refusal precision",
            "display": _format_percent(summary["refusal_precision"]),
            "gate": "≥ 85%",
            "outcome": _gate_min(summary["refusal_precision"], 0.85),
        },
        {
            "key": "judge_correctness",
            "label": "Correctness",
            "display": _format_judge(summary["judge_correctness"]),
            "gate": "Judge score · informational",
            "outcome": "info",
        },
        {
            "key": "judge_faithfulness",
            "label": "Faithfulness",
            "display": _format_judge(summary["judge_faithfulness"]),
            "gate": "Judge score · informational",
            "outcome": "info",
        },
        {
            "key": "p95_latency_ms",
            "label": "P95 latency",
            "display": _format_latency(summary["p95_latency_ms"]),
            "gate": "≤ 8s",
            "outcome": _gate_max(summary["p95_latency_ms"], 8000),
        },
    ]

    gated = [card for card in metric_cards if card["outcome"] in {"pass", "fail"}]

    return {
        "cases": summary["cases"],
        "provider_failures": summary["provider_failures"],
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "gates_met": (
            all(card["outcome"] == "pass" for card in gated)
            if gated
            else None
        ),
        "metric_cards": metric_cards,
    }


def _public_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": run["run_id"],
        "status": run["status"],
        "test_set": run["test_set"],
        "test_set_label": run["test_set_label"],
        "model": run["model"],
        "use_judge": run["use_judge"],
        "judge_model": run["judge_model"],
        "retrieval_strategy": run["retrieval_strategy"],
        "top_k": run["top_k"],
        "completed": run["completed"],
        "total": run["total"],
        "passed": run["passed"],
        "failed": run["failed"],
        "remaining": max(0, run["total"] - run["completed"]),
        "current_case": run["current_case"],
        "elapsed_seconds": run["elapsed_seconds"],
        "started_at": run["started_at"],
        "finished_at": run["finished_at"],
        "error": run["error"],
        "summary": run["summary"],
    }


def _public_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return one evaluation case with its failure reasons."""

    return {
        "id": result.get("id"),
        "class": result.get("class"),
        "use_case": result.get("use_case"),
        "question": result.get("question"),
        "expected_source": result.get("expected_source"),
        "expected_sources": result.get("expected_sources", []),
        "expected_outcome": result.get("expected_outcome"),
        "must_refuse": result.get("must_refuse", False),
        "model_name": result.get("model_name"),
        "retrieval_strategy": result.get("retrieval_strategy"),
        "top_k": result.get("top_k"),
        "model_answer": result.get("model_answer"),
        "retrieved_files": result.get("retrieved_files", []),
        "retrieved_chunks": result.get("retrieved_chunks", []),
        "metrics": result.get("metrics", {}),
        "judge": result.get("judge"),
        "retrieval_latency_ms": result.get("retrieval_latency_ms"),
        "generation_latency_ms": result.get("generation_latency_ms"),
        "latency_ms": result.get("latency_ms"),
        "status": result.get("status", "ok"),
        "created_at": result.get("created_at"),
        "failures": case_failures(result),
    }


def _refresh_progress(run_id: str) -> None:
    with _runs_lock:
        run = _runs.get(run_id)
        if run is None:
            return
        output_path = Path(run["output_path"])
        case_ids = list(run["case_ids"])
        started_monotonic = float(run["started_monotonic"])

    results = _read_results(output_path)

    passed = sum(1 for result in results if not case_failures(result))
    failed = len(results) - passed
    completed = len(results)
    current_case = case_ids[completed] if completed < len(case_ids) else None

    with _runs_lock:
        run = _runs.get(run_id)
        if run is None:
            return

        run["completed"] = completed
        run["passed"] = passed
        run["failed"] = failed
        run["current_case"] = current_case
        run["elapsed_seconds"] = max(
            0,
            int(time.monotonic() - started_monotonic),
        )


def _monitor_run(
    run_id: str,
    process: subprocess.Popen[str],
    log_file: Any,
) -> None:
    global _active_run_id

    try:
        while process.poll() is None:
            _refresh_progress(run_id)
            time.sleep(0.75)

        _refresh_progress(run_id)

        with _runs_lock:
            run = _runs.get(run_id)
            if run is None:
                return

            stop_requested = bool(run["stop_requested"])
            output_path = Path(run["output_path"])

        results = _read_results(output_path)
        summary = _build_summary(results) if results else None

        with _runs_lock:
            run = _runs.get(run_id)
            if run is None:
                return

            if stop_requested:
                run["status"] = "interrupted"
                run["error"] = None
            elif process.returncode == 0:
                run["status"] = "completed"
                run["error"] = None
            else:
                run["status"] = "failed"
                run["error"] = (
                    "The evaluation run stopped before completion. "
                    "Check the server log and retry the run."
                )

            run["summary"] = summary
            run["finished_at"] = _utc_now()
            run["current_case"] = None

            if _active_run_id == run_id:
                _active_run_id = None

    except Exception:
        logger.exception("evaluation_monitor_failed run_id=%s", run_id)

        with _runs_lock:
            run = _runs.get(run_id)
            if run is not None:
                run["status"] = "failed"
                run["error"] = "The evaluation status monitor failed."
                run["finished_at"] = _utc_now()
                run["current_case"] = None

            if _active_run_id == run_id:
                _active_run_id = None

    finally:
        try:
            log_file.close()
        except Exception:
            pass


def _launch_monitor(
    run_id: str,
    process: subprocess.Popen[str],
    log_file: Any,
) -> None:
    thread = threading.Thread(
        target=_monitor_run,
        args=(run_id, process, log_file),
        daemon=True,
        name=f"evaluation-run-{run_id}",
    )
    thread.start()


@router.get("/config")
def evaluation_config(request: Request) -> dict[str, Any]:
    _require_team(request)

    test_sets = []
    for test_set_id, item in TEST_SETS.items():
        path = _test_set_path(test_set_id)
        test_sets.append(
            {
                "id": test_set_id,
                "label": item["label"],
                "case_count": len(load_cases(path)),
            }
        )

    return {
        "test_sets": test_sets,
        "models": MODEL_OPTIONS,
        "retrieval_strategies": sorted(RETRIEVAL_STRATEGIES),
        "defaults": {
            "test_set": "core-mvp",
            "model": _default_model(),
            "retrieval_strategy": DEFAULT_RETRIEVAL_STRATEGY,
            "top_k": DEFAULT_TOP_K,
        },
    }


@router.get("/runs/active")
def get_active_evaluation_run(
    request: Request,
) -> dict[str, Any]:
    _require_team(request)

    with _runs_lock:
        run_id = _active_run_id

    if not run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation run is active.",
        )

    _refresh_progress(run_id)

    with _runs_lock:
        run = _runs.get(run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evaluation run not found.",
            )
        return _public_run(run)


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
def start_evaluation_run(
    body: StartRunRequest,
    request: Request,
) -> dict[str, Any]:
    global _active_run_id

    _require_team(request)
    questions_path, judge_model = _validate_request(body)

    cases = load_cases(questions_path)
    run_id = uuid.uuid4().hex[:12]
    output_path = RUN_DIR / f"{run_id}.jsonl"
    log_path = RUN_DIR / f"{run_id}.log"

    with _runs_lock:
        if _active_run_id is not None:
            active = _runs.get(_active_run_id)
            if active and active.get("status") not in TERMINAL_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Another evaluation run is already active.",
                )
            _active_run_id = None

        state: dict[str, Any] = {
            "run_id": run_id,
            "status": "starting",
            "test_set": body.test_set,
            "test_set_label": TEST_SETS[body.test_set]["label"],
            "model": body.model,
            "use_judge": body.use_judge,
            "judge_model": judge_model,
            "retrieval_strategy": body.retrieval_strategy.strip().lower(),
            "top_k": body.top_k,
            "completed": 0,
            "total": len(cases),
            "passed": 0,
            "failed": 0,
            "current_case": cases[0]["id"] if cases else None,
            "elapsed_seconds": 0,
            "started_at": _utc_now(),
            "finished_at": None,
            "started_monotonic": time.monotonic(),
            "error": None,
            "summary": None,
            "stop_requested": False,
            "output_path": str(output_path),
            "log_path": str(log_path),
            "case_ids": [case["id"] for case in cases],
            "process": None,
        }

        _runs[run_id] = state
        _active_run_id = run_id

    command = _build_command(
        questions_path=questions_path,
        output_path=output_path,
        model=body.model,
        top_k=body.top_k,
        retrieval_strategy=body.retrieval_strategy.strip().lower(),
        judge_model=judge_model,
    )

    try:
        process, log_file = _spawn_process(
            command=command,
            log_path=log_path,
        )
    except Exception:
        logger.exception("evaluation_start_failed run_id=%s", run_id)

        with _runs_lock:
            run = _runs[run_id]
            run["status"] = "failed"
            run["error"] = "The evaluation run could not be started."
            run["finished_at"] = _utc_now()
            if _active_run_id == run_id:
                _active_run_id = None

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The evaluation run could not be started.",
        ) from None

    with _runs_lock:
        run = _runs[run_id]
        run["process"] = process
        run["status"] = "running"

    _launch_monitor(run_id, process, log_file)

    with _runs_lock:
        return _public_run(_runs[run_id])


@router.get("/runs/{run_id}")
def get_evaluation_run(
    run_id: str,
    request: Request,
) -> dict[str, Any]:
    _require_team(request)
    _refresh_progress(run_id)

    with _runs_lock:
        run = _runs.get(run_id)

        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evaluation run not found.",
            )

        return _public_run(run)


@router.get("/runs/{run_id}/results")
def get_evaluation_run_results(
    run_id: str,
    request: Request,
) -> dict[str, Any]:
    """Return already-recorded per-question results for a run."""

    _require_team(request)

    with _runs_lock:
        run = _runs.get(run_id)

        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evaluation run not found.",
            )

        output_path = Path(run["output_path"])
        run_status = run["status"]

    results = _read_results(output_path)

    return {
        "run_id": run_id,
        "status": run_status,
        "completed": len(results),
        "results": [
            _public_result(result)
            for result in results
        ],
    }


@router.post("/runs/{run_id}/stop")
def stop_evaluation_run(
    run_id: str,
    request: Request,
) -> dict[str, Any]:
    _require_team(request)

    with _runs_lock:
        run = _runs.get(run_id)

        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evaluation run not found.",
            )

        if run["status"] in TERMINAL_STATUSES:
            return _public_run(run)

        process = run.get("process")
        run["stop_requested"] = True
        run["status"] = "stopping"

    if process is not None and process.poll() is None:
        try:
            process.terminate()
        except Exception:
            logger.exception("evaluation_stop_failed run_id=%s", run_id)

    with _runs_lock:
        return _public_run(_runs[run_id])
