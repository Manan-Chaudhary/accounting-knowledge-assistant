import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from litellm import completion
from litellm.exceptions import ServiceUnavailableError

from app.config import settings

from app.rag.generator import SYSTEM_PROMPT_TEMPLATE, get_formatted_prompt
from app.rag.retriever import format_retrieved_context, retrieve


DEFAULT_MODEL = "gemini/gemini-3.8-flash"
DEFAULT_TOP_K = 6


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    """Load evaluation cases from a JSONL file."""

    cases: list[dict[str, Any]] = []

    with Path(path).open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            case = json.loads(line)

            if "id" not in case:
                raise ValueError(
                    f"Evaluation case on line {line_number} is missing 'id'."
                )

            if "question" not in case:
                raise ValueError(
                    f"Evaluation case {case['id']} is missing 'question'."
                )

            cases.append(case)

    return cases


def generate_with_model(
    query: str,
    context: str,
    model: str,
    max_attempts: int = 4,
) -> str:
    """
    Generate an evaluation response using LiteLLM directly.

    Retries temporary provider availability failures.
    """

    prompt = get_formatted_prompt(
        query=query,
        context=context,
    )

    for attempt in range(1, max_attempts + 1):
        try:
            response = completion(
                model=model,
                api_key=settings.GEMINI_API_KEY,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_TEMPLATE,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

            return response.choices[0].message.content or ""

        except ServiceUnavailableError:
            if attempt == max_attempts:
                raise

            wait_seconds = 2 ** (attempt - 1)

            print(
                f"    Model temporarily unavailable. "
                f"Retrying in {wait_seconds}s "
                f"({attempt}/{max_attempts})..."
            )

            time.sleep(wait_seconds)

    raise RuntimeError("Model generation failed unexpectedly.")

def run_case(
    case: dict[str, Any],
    model: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:
    """Run one evaluation case through retrieval and generation."""

    question = str(case["question"]).strip()

    retrieval_start = time.perf_counter()

    chunks = retrieve(
        query=question,
        top_k=top_k,
    )

    retrieval_latency_ms = round(
        (time.perf_counter() - retrieval_start) * 1000
    )

    context = format_retrieved_context(chunks)

    generation_start = time.perf_counter()

    answer = generate_with_model(
        query=question,
        context=context,
        model=model,
    )

    generation_latency_ms = round(
        (time.perf_counter() - generation_start) * 1000
    )

    retrieved_files = [chunk.filename for chunk in chunks]

    expected_source = case.get("expected_source")

    if expected_source:
        source_hit = expected_source in retrieved_files
    else:
        source_hit = None

    citation_present = bool(
        re.search(r"\[\d+\]", answer)
    )

    retrieved_chunks = [
        {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "filename": chunk.filename,
            "source_label": chunk.source_label,
            "similarity": round(chunk.similarity, 4),
            "content_preview": chunk.content[:400],
        }
        for chunk in chunks
    ]

    return {
        "id": case["id"],
        "class": case.get("class"),
        "question": question,
        "expected_source": expected_source,
        "expected_outcome": case.get("expected_outcome"),
        "must_refuse": case.get("must_refuse", False),
        "model_name": model,
        "model_answer": answer,
        "retrieved_chunk_ids": [
            chunk.chunk_id for chunk in chunks
        ],
        "retrieved_files": retrieved_files,
        "retrieved_chunks": retrieved_chunks,
        "metrics": {
            "answer_returned": bool(answer.strip()),
            "expected_source_hit": source_hit,
            "citation_present": citation_present,
        },
        "retrieval_latency_ms": retrieval_latency_ms,
        "generation_latency_ms": generation_latency_ms,
        "latency_ms": (
            retrieval_latency_ms + generation_latency_ms
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_suite(
    questions_path: str | Path,
    output_path: str | Path,
    model: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    """Run all evaluation cases and save each result incrementally."""

    cases = load_cases(questions_path)

    results: list[dict[str, Any]] = []

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Start a fresh result file for this run.
    output.write_text("", encoding="utf-8")

    for index, case in enumerate(cases, start=1):
        print(
            f"[{index}/{len(cases)}] Running "
            f"{case['id']}: {case['question']}"
        )

        try:
            result = run_case(
                case=case,
                model=model,
                top_k=top_k,
            )

            print(
                "    "
                f"source_hit={result['metrics']['expected_source_hit']} "
                f"citation={result['metrics']['citation_present']} "
                f"latency={result['latency_ms']}ms"
            )

        except ServiceUnavailableError as exc:
            result = {
                "id": case["id"],
                "class": case.get("class"),
                "question": case["question"],
                "expected_source": case.get("expected_source"),
                "expected_outcome": case.get("expected_outcome"),
                "must_refuse": case.get("must_refuse", False),
                "model_name": model,
                "model_answer": None,
                "retrieved_chunk_ids": [],
                "retrieved_files": [],
                "retrieved_chunks": [],
                "metrics": {
                    "answer_returned": False,
                    "expected_source_hit": None,
                    "citation_present": False,
                    "provider_available": False,
                },
                "retrieval_latency_ms": None,
                "generation_latency_ms": None,
                "latency_ms": None,
                "status": "provider_unavailable",
                "error": str(exc),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            print(
                "    Provider unavailable after retries. "
                "Recorded failure and continuing."
            )

        results.append(result)

        # Save immediately so completed cases are never lost.
        with output.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(result, ensure_ascii=False)
                + "\n"
            )

    return results

