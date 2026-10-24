# LLM Model Evaluation Report

> **Status: rewritten to match the files in `benchmarks/`.** An earlier version of this report quoted Gemini figures (94.2% citation precision, a 30-case run, 96.7% corpus separation, 100% PII redaction, 1.15 s latency) and recommended a Gemini primary with a Groq fallback. None of those figures appear in any file under `benchmarks/results/` or `benchmarks/reports/`, so they were removed. **No verified head-to-head comparison of Gemini against the Groq models exists.** No model has been formally selected on evidence.

## 1. What was actually run

- **Harness and benchmark:** `scripts/run_evaluation.py` over the first 22 cases of `benchmarks/questions.jsonl`. The file now holds 50 cases, but every saved result file covers only 22 (EVAL-001 to EVAL-022).
- **Prompt and routing:** the system prompt in `app/rag/generator.py`, with generation through the LiteLLM proxy.
- **Metrics:** defined in [`EVALUATION.md`](EVALUATION.md) section 4. Rates exclude cases where a metric does not apply.
- **Not measured:** PII redaction, "Corpus A/B separation" and any cost figure. The harness does not produce them.

## 2. Three-model comparison (the only multi-model result)

Source: `benchmarks/reports/comparison_2026-10-01.md` (generated 2026-10-01). All three are Groq models, 22 cases, 0 provider failures.

| Metric | gpt-oss-120b | qwen3.8-27b | gpt-oss-20b |
|---|---|---|---|
| Source hit / Recall@k / MRR | 100% / 1.00 / 0.96 | 100% / 1.00 / 0.96 | 100% / 1.00 / 0.96 |
| Citation present (answerable) | 94% | 100% | 94% |
| Citation valid | 94% | 85% | 94% |
| Citation format `[n]` | 88% | 100% | 69% |
| Refusal correct | 95% | 100% | 91% |
| Refusal recall / precision | 100% / 86% | 100% / 100% | 83% / 83% |
| Judge correctness (1-5) | 4.38 | 4.19 | 4.38 |
| Judge faithfulness (1-5) | 4.69 | 4.38 | 4.12 |
| P50 / P95 latency | 30.0 s / 44.8 s | 32.0 s / 152.1 s | 29.4 s / 36.2 s |

Retrieval is identical across the three because retrieval does not depend on the model. The models differ on citation discipline, refusal behaviour and tail latency. With 22 cases, differences of one or two cases are noise. The judge scores come from an LLM judge and are not deterministic.

## 3. Gemini results (single model, retrieval-mode runs)

`gemini/gemini-3.8-flash` appears only in retrieval-mode reports, not in a model comparison, and those runs have no judge scores:

| Run (report) | Date | Cases | Source hit | Citation valid | Refusal correct | P50 / P95 latency |
|---|---|---|---|---|---|---|
| Dense only (`dense.md`) | 2026-10-04 | 22 | 100% | 100% | 95% | 8.4 s / 135.8 s |
| Keyword only (`keyword.md`) | 2026-10-06 | 22 | 41% | 100% | 64% | 10.9 s / 163.1 s |

`benchmarks/results/hybrid.jsonl` holds only 4 cases and `sample_gemini_3_8_flash.jsonl` 4 cases, too few to report. The Gemini latency measurement of 14 October (`benchmarks/reports/LATENCY_BREAKDOWN_REPORT_2026-10-14.md`, hybrid retrieval, no reranker at the time) gave a P95 of 176.8 s, dominated by time to first token on free-tier routing.

## 4. What can and cannot be concluded

- Retrieval is strong on this small set (100% source hit with dense retrieval) and keyword-only retrieval is much weaker (41%).
- Among the Groq models, none is clearly best: qwen3.8-27b has the best refusal and citation-presence numbers but the worst citation validity and a 152 s P95; gpt-oss-20b has the lowest latency but the weakest faithfulness and `[n]` format adherence.
- Every measured configuration is far above the 8 s P95 target, with free-tier routing the main suspect.
- A Gemini versus Groq decision needs a like-for-like run (same 50 cases, same judge, reranker on). That has not been done.
- The deployed default is whatever `LITELLM_MODEL` and `litellm/config.yaml` specify. That is a configuration choice, not an evaluation result.
