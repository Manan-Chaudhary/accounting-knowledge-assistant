import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from litellm import completion
from litellm.exceptions import RateLimitError, ServiceUnavailableError

from app.config import settings

from app.rag.generator import SYSTEM_PROMPT_TEMPLATE, get_formatted_prompt
from app.rag.retriever import format_retrieved_context, retrieve


DEFAULT_MODEL = "gemini/gemini-3.8-flash"
DEFAULT_TOP_K = 6

RETRYABLE_ERRORS = (ServiceUnavailableError, RateLimitError)

CITATION_PATTERN = re.compile(r"\[(\d+)\]")
# Some models cite with CJK lenticular brackets, which the chat UI does not render as citations.
NONSTANDARD_CITATION_PATTERN = re.compile(r"【(\d+)[^】]*】")

# Phrases taken from the refusal and escalation templates in docs/PROMPTS.md
# section 2, plus the wording the system prompt rules ask for.
REFUSAL_PATTERNS = [
    r"(could|can) ?(not|n't|n’t) (find|locate)",
    r"can(no|'|’)t (confirm|verify)",
    r"(unable|not able) to (locate|confirm|verify|find|provide)",
    r"no (supporting|relevant) (source|authority)",
    r"(do|does) not (appear|contain)[^.]{0,60}(context|sources)",
    r"not (going|able) to answer",
    r"depends on data i do not hold",
    r"specific to the member",
    r"recommendation for the practitioner",
    r"not something i can (answer|state|recommend)",
    r"outside (the )?(scope|indexed sources|these sources)",
]
REFUSAL_REGEX = re.compile("|".join(REFUSAL_PATTERNS), re.IGNORECASE)


JUDGE_PROMPT = """You are grading an answer from an accounting knowledge assistant.

Question:
{question}

Reference answer:
{expected_answer}

Retrieved context given to the assistant:
{context}

Assistant answer:
{answer}

Score two things from 1 (worst) to 5 (best):
- correctness: how well the answer agrees with the reference answer. Missing a key rule or figure lowers the score; a wrong figure scores 1 or 2.
- faithfulness: whether every claim in the answer is supported by the retrieved context. Claims from outside the context lower the score.

Return JSON only, in this exact shape:
{{"correctness": <1-5>, "faithfulness": <1-5>, "reason": "<one sentence>"}}"""


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

            case["expected_sources"] = expected_sources_for(case)

            cases.append(case)

    return cases


def expected_sources_for(case: dict[str, Any]) -> list[str]:
    """Return the case's expected sources, accepting the older single-source field."""

    sources = case.get("expected_sources")

    if sources:
        return list(sources)

    if case.get("expected_source"):
        return [case["expected_source"]]

    return []


def api_key_for(model: str) -> str | None:
    """Pick the provider key for a LiteLLM model name from its prefix."""

    provider = model.split("/", 1)[0]

    keys = {
        "gemini": settings.GEMINI_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "openai": settings.OPENAI_API_KEY,
    }

    return keys.get(provider) or None


def retry_wait_seconds(error: Exception, attempt: int) -> float:
    """Back off exponentially, or for rate limits use the provider's retry hint."""

    if isinstance(error, RateLimitError):
        hint = re.search(r"try again in ([\d.]+)s", str(error))

        return float(hint.group(1)) + 2 if hint else 15.0 * attempt

    return 2 ** attempt


def complete_with_retry(
    model: str,
    messages: list[dict[str, str]],
    max_attempts: int = 6,
    **kwargs: Any,
) -> str:
    """Call LiteLLM directly, retrying temporary availability and rate-limit failures."""

    for attempt in range(1, max_attempts + 1):
        try:
            response = completion(
                model=model,
                api_key=api_key_for(model),
                messages=messages,
                **kwargs,
            )

            return response.choices[0].message.content or ""

        except RETRYABLE_ERRORS as exc:
            if attempt == max_attempts:
                raise

            wait_seconds = retry_wait_seconds(exc, attempt)

            print(
                f"    Model temporarily unavailable or rate limited. "
                f"Retrying in {wait_seconds}s "
                f"({attempt}/{max_attempts})..."
            )

            time.sleep(wait_seconds)

    raise RuntimeError("Model generation failed unexpectedly.")


def generate_with_model(
    query: str,
    context: str,
    model: str,
) -> str:
    """Generate an evaluation response with the production system prompt."""

    prompt = get_formatted_prompt(
        query=query,
        context=context,
    )

    return complete_with_retry(
        model=model,
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


def judge_answer(
    question: str,
    expected_answer: str,
    context: str,
    answer: str,
    judge_model: str,
) -> dict[str, Any]:
    """Score correctness and faithfulness with an LLM judge."""

    # A judge outage should not discard the answer being judged.
    try:
        raw = complete_with_retry(
            model=judge_model,
            messages=[
                {
                    "role": "user",
                    "content": JUDGE_PROMPT.format(
                        question=question,
                        expected_answer=expected_answer,
                        context=context,
                        answer=answer,
                    ),
                }
            ],
            temperature=0,
        )
    except RETRYABLE_ERRORS as exc:
        return {"judge_model": judge_model, "error": f"judge unavailable: {exc}"}

    match = re.search(r"\{.*\}", raw, re.DOTALL)

    if not match:
        return {"judge_model": judge_model, "error": "no JSON in judge output"}

    try:
        scores = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"judge_model": judge_model, "error": "invalid JSON in judge output"}

    return {
        "judge_model": judge_model,
        "correctness": scores.get("correctness"),
        "faithfulness": scores.get("faithfulness"),
        "reason": scores.get("reason"),
    }


def retrieval_metrics(
    expected_sources: list[str],
    retrieved_files: list[str],
) -> dict[str, Any]:
    """Source-level retrieval metrics. All None when the case has no expected source."""

    if not expected_sources:
        return {
            "expected_source_hit": None,
            "top1_source_hit": None,
            "recall_at_k": None,
            "reciprocal_rank": None,
        }

    expected = set(expected_sources)
    found = expected & set(retrieved_files)

    first_rank = next(
        (
            rank
            for rank, filename in enumerate(retrieved_files, start=1)
            if filename in expected
        ),
        None,
    )

    return {
        "expected_source_hit": bool(found),
        "top1_source_hit": bool(retrieved_files) and retrieved_files[0] in expected,
        "recall_at_k": round(len(found) / len(expected), 4),
        "reciprocal_rank": round(1 / first_rank, 4) if first_rank else 0.0,
    }


def citation_metrics(answer: str, chunk_count: int) -> dict[str, Any]:
    """Check that every citation marker points at a retrieved chunk and uses the [n] format."""

    standard = [int(n) for n in CITATION_PATTERN.findall(answer)]
    nonstandard = [int(n) for n in NONSTANDARD_CITATION_PATTERN.findall(answer)]
    markers = standard + nonstandard
    invalid = sorted({n for n in markers if n < 1 or n > chunk_count})

    return {
        "citation_present": bool(markers),
        "citation_valid": (not invalid) if markers else None,
        "citation_format_standard": (not nonstandard) if markers else None,
        "invalid_citations": invalid,
    }


def rescore(result: dict[str, Any]) -> dict[str, Any]:
    """Recompute the deterministic metrics of a stored result from its saved answer.

    Lets scoring changes be applied to earlier runs without calling the model again.
    """

    if result.get("status", "ok") != "ok":
        return result

    answer = result.get("model_answer") or ""
    refused = is_refusal(answer)

    result["metrics"].update(
        {
            **retrieval_metrics(expected_sources_for(result), result["retrieved_files"]),
            **citation_metrics(answer, len(result["retrieved_files"])),
            "refused": refused,
            "refusal_correct": refused == bool(result.get("must_refuse")),
        }
    )

    return result


def is_refusal(answer: str) -> bool:
    return bool(REFUSAL_REGEX.search(answer or ""))


def run_case(
    case: dict[str, Any],
    model: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
    judge_model: str | None = None,
) -> dict[str, Any]:
    """Run one evaluation case through retrieval and generation."""

    question = str(case["question"]).strip()
    expected_sources = expected_sources_for(case)
    must_refuse = bool(case.get("must_refuse", False))

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

    refused = is_refusal(answer)

    metrics = {
        "answer_returned": bool(answer.strip()),
        **retrieval_metrics(expected_sources, retrieved_files),
        **citation_metrics(answer, len(chunks)),
        "refused": refused,
        "refusal_correct": refused == must_refuse,
        "provider_available": True,
    }

    judge = None

    if judge_model and case.get("expected_answer") and answer.strip():
        judge = judge_answer(
            question=question,
            expected_answer=case["expected_answer"],
            context=context,
            answer=answer,
            judge_model=judge_model,
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
        "use_case": case.get("use_case"),
        "question": question,
        "expected_source": case.get("expected_source"),
        "expected_sources": expected_sources,
        "expected_outcome": case.get("expected_outcome"),
        "expected_answer": case.get("expected_answer"),
        "must_refuse": must_refuse,
        "model_name": model,
        "top_k": top_k,
        "model_answer": answer,
        "retrieved_chunk_ids": [
            chunk.chunk_id for chunk in chunks
        ],
        "retrieved_files": retrieved_files,
        "retrieved_chunks": retrieved_chunks,
        "metrics": metrics,
        "judge": judge,
        "retrieval_latency_ms": retrieval_latency_ms,
        "generation_latency_ms": generation_latency_ms,
        "latency_ms": (
            retrieval_latency_ms + generation_latency_ms
        ),
        "status": "ok",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def failed_case_result(
    case: dict[str, Any],
    model: str,
    top_k: int,
    error: Exception,
) -> dict[str, Any]:
    """Result record for a case the provider could not answer after retries."""

    return {
        "id": case["id"],
        "class": case.get("class"),
        "use_case": case.get("use_case"),
        "question": case["question"],
        "expected_source": case.get("expected_source"),
        "expected_sources": expected_sources_for(case),
        "expected_outcome": case.get("expected_outcome"),
        "expected_answer": case.get("expected_answer"),
        "must_refuse": bool(case.get("must_refuse", False)),
        "model_name": model,
        "top_k": top_k,
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
        "judge": None,
        "retrieval_latency_ms": None,
        "generation_latency_ms": None,
        "latency_ms": None,
        "status": "provider_unavailable",
        "error": str(error),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_suite(
    questions_path: str | Path,
    output_path: str | Path,
    model: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
    judge_model: str | None = None,
) -> list[dict[str, Any]]:
    """Run all evaluation cases and save each result incrementally."""

    cases = load_cases(questions_path)

    run_id = uuid.uuid4().hex[:12]

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
                judge_model=judge_model,
            )

            print(
                "    "
                f"source_hit={result['metrics']['expected_source_hit']} "
                f"citation_valid={result['metrics']['citation_valid']} "
                f"refusal_correct={result['metrics']['refusal_correct']} "
                f"latency={result['latency_ms']}ms"
            )

        except RETRYABLE_ERRORS as exc:
            result = failed_case_result(case, model, top_k, exc)

            print(
                "    Provider unavailable after retries. "
                "Recorded failure and continuing."
            )

        result["run_id"] = run_id

        results.append(result)

        # Save immediately so completed cases are never lost.
        with output.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(result, ensure_ascii=False)
                + "\n"
            )

    return results
