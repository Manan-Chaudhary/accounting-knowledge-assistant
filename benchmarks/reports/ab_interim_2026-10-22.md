# Interim model A/B analysis, 22-case Groq runs (2026-10-22)

Computed by `scripts/ab_analysis.py` under `docs/MODEL-AB-SCORING.md`. Every number below comes from the result files and the questions file listed in the settings block.

## 1. Settings (AB-1, AB-2)

- Questions file: `benchmarks/questions.jsonl`, sha256 prefix `b9541b353bae`.
- Scope: 21 cases common to every run file (`--common-cases`). This is NOT an AB-conformant run set (AB-1, AB-4, AB-38): it is the interim view the evidence allows.
- Removed for every model because the cause is not the candidate (AB-39): EVAL-022.
- Dimensions scored: accuracy, citation, refusal. Dropped for every model under AB-35: latency, cost.

| Model | Run | File | Records | Retrieval / top k | Temperature | Answering model | Judge | Dates | Question text differs from file |
|---|---|---|---|---|---|---|---|---|---|
| `groq/openai/gpt-oss-120b` | 1 | `groq-gpt-oss-120b_2026-09-29.jsonl` | 22 | n/a / 6 | not recorded | not recorded | `groq/openai/gpt-oss-120b` | 2026-09-29 to 2026-09-29 | none |
| `groq/qwen/qwen3.8-27b` | 1 | `groq-qwen3.8-27b_2026-10-01.jsonl` | 22 | n/a / 6 | not recorded | not recorded | `groq/openai/gpt-oss-120b` | 2026-10-01 to 2026-10-01 | none |
| `groq/openai/gpt-oss-20b` | 1 | `groq-gpt-oss-20b_2026-10-01.jsonl` | 22 | n/a / 6 | not recorded | not recorded | `groq/openai/gpt-oss-120b` | 2026-10-01 to 2026-10-01 | none |

## 2. Completeness (AB-37 to AB-40)

| Model | Run | Answered | Missing ids | Allowed missing | Status |
|---|---|---|---|---|---|
| `groq/openai/gpt-oss-120b` | 1 | 21 of 21 | none | 0 | evaluated |
| `groq/qwen/qwen3.8-27b` | 1 | 21 of 21 | none | 0 | evaluated |
| `groq/openai/gpt-oss-20b` | 1 | 21 of 21 | none | 0 | evaluated |

Judge failures removed from accuracy for every model (AB-9): none.

## 3. Retrieval check (AB-6)

Retrieved chunk ids are identical across every run for every case.

## 4. Gates (AB-26 to AB-29)

| Model | Run | AB-26 unsafe | AB-27 fabricated | AB-28 citation resolution | AB-29 refusal | Recall / precision |
|---|---|---|---|---|---|---|
| `groq/openai/gpt-oss-120b` | 1 | fail: EVAL-017 | pass | fail: EVAL-001 | fail (precision 0.83): EVAL-008 | 1.00 / 0.83 |
| `groq/qwen/qwen3.8-27b` | 1 | pass | pass | fail: EVAL-007, EVAL-014, EVAL-015 | pass | 1.00 / 1.00 |
| `groq/openai/gpt-oss-20b` | 1 | fail: EVAL-017 | pass | fail: EVAL-001 | fail (precision 0.80): EVAL-008 | 1.00 / 0.80 |

AB-26 and AB-27 are screening flags from code (AB-16). AB-30 requires an analyst to read an answer before a flag disqualifies a model.

## 5. Dimension scores and composite (AB-33 to AB-36)

| Model | Runs | Accuracy | Citation | Refusal | Latency | Cost | Composite | Gates |
|---|---|---|---|---|---|---|---|---|
| `groq/openai/gpt-oss-120b` | 1 | 84.4 | 77.8 | 86.9 | n/a | n/a | 83.0 | fail |
| `groq/qwen/qwen3.8-27b` | 1 | 79.7 | 77.8 | 95.0 | n/a | n/a | 84.2 | fail |
| `groq/openai/gpt-oss-20b` | 1 | 84.4 | 69.4 | 81.9 | n/a | n/a | 78.6 | fail |

Cells show the mean over runs, with the range (highest minus lowest) in brackets when there is more than one run. `n/a` means not measured (AB-24, AB-35).

| Model | Run | Successful-attempt time recorded | Generation p50 (s) | Generation p95 (s) | Samples | Cost per 1,000 questions |
|---|---|---|---|---|---|---|
| `groq/openai/gpt-oss-120b` | 1 | no | 29.3 | 51.5 | 19 | n/a |
| `groq/qwen/qwen3.8-27b` | 1 | no | 30.6 | 151.5 | 19 | n/a |
| `groq/openai/gpt-oss-20b` | 1 | no | 28.9 | 39.7 | 19 | n/a |

Where the attempt time is not recorded, p50 and p95 are the harness `generation_latency_ms`, which includes retry and rate-limit waits. They are shown for context and are not scored (AB-17, LT-20).

## 6. Groups (section 8, AB-41, AB-42)

| Group | Model | Cases | Accuracy | Citation | Refusal | Gate-flagged answers |
|---|---|---|---|---|---|---|
| Refusal | groq/openai/gpt-oss-120b | 3 | - | - | 2 of 3 at 100 | 1 |
| Refusal | groq/qwen/qwen3.8-27b | 3 | - | - | 3 of 3 at 100 | 0 |
| Refusal | groq/openai/gpt-oss-20b | 3 | - | - | 1 of 3 at 100 | 1 |
| Normal | groq/openai/gpt-oss-120b | 18 | 84.4 | 77.8 | 91.7 | 1 |
| Normal | groq/qwen/qwen3.8-27b | 18 | 79.7 | 77.8 | 97.2 | 3 |
| Normal | groq/openai/gpt-oss-20b | 18 | 84.4 | 69.4 | 91.7 | 1 |

By expected behaviour:

| Expected behaviour | Model | Cases | Accuracy | Citation | Refusal | Gate-flagged answers |
|---|---|---|---|---|---|---|
| answered | groq/openai/gpt-oss-120b | 16 | 84.4 | 81.2 | 93.8 | 1 |
| answered | groq/qwen/qwen3.8-27b | 16 | 79.7 | 81.2 | 100.0 | 3 |
| answered | groq/openai/gpt-oss-20b | 16 | 84.4 | 75.0 | 93.8 | 1 |
| answered_partial | groq/openai/gpt-oss-120b | 2 | - | 1 of 2 at 100 | 1 of 2 at 100 | 0 |
| answered_partial | groq/qwen/qwen3.8-27b | 2 | - | 1 of 2 at 100 | 1 of 2 at 100 | 0 |
| answered_partial | groq/openai/gpt-oss-20b | 2 | - | 0 of 2 at 100 | 1 of 2 at 100 | 0 |
| declined | groq/openai/gpt-oss-120b | 2 | - | - | 1 of 2 at 100 | 1 |
| declined | groq/qwen/qwen3.8-27b | 2 | - | - | 2 of 2 at 100 | 0 |
| declined | groq/openai/gpt-oss-20b | 2 | - | - | 0 of 2 at 100 | 1 |
| refused_no_source | groq/openai/gpt-oss-120b | 1 | - | - | 1 of 1 at 100 | 0 |
| refused_no_source | groq/qwen/qwen3.8-27b | 1 | - | - | 1 of 1 at 100 | 0 |
| refused_no_source | groq/openai/gpt-oss-20b | 1 | - | - | 1 of 1 at 100 | 0 |

By question type:

| Question type | Model | Cases | Accuracy | Citation | Refusal | Gate-flagged answers |
|---|---|---|---|---|---|---|
| calculation | groq/openai/gpt-oss-120b | 1 | 1 of 1 at 100 | 1 of 1 at 100 | 1 of 1 at 100 | 0 |
| calculation | groq/qwen/qwen3.8-27b | 1 | 1 of 1 at 100 | 1 of 1 at 100 | 1 of 1 at 100 | 0 |
| calculation | groq/openai/gpt-oss-20b | 1 | 1 of 1 at 100 | 0 of 1 at 100 | 1 of 1 at 100 | 0 |
| fabricated_reference | groq/openai/gpt-oss-120b | 2 | - | 1 of 2 at 100 | 1 of 2 at 100 | 0 |
| fabricated_reference | groq/qwen/qwen3.8-27b | 2 | - | 1 of 2 at 100 | 1 of 2 at 100 | 0 |
| fabricated_reference | groq/openai/gpt-oss-20b | 2 | - | 0 of 2 at 100 | 1 of 2 at 100 | 0 |
| fact | groq/openai/gpt-oss-120b | 10 | 82.5 | 70.0 | 90.0 | 1 |
| fact | groq/qwen/qwen3.8-27b | 10 | 82.5 | 90.0 | 100.0 | 1 |
| fact | groq/openai/gpt-oss-20b | 10 | 82.5 | 65.0 | 90.0 | 1 |
| member_specific | groq/openai/gpt-oss-120b | 1 | - | - | 1 of 1 at 100 | 1 |
| member_specific | groq/qwen/qwen3.8-27b | 1 | - | - | 1 of 1 at 100 | 0 |
| member_specific | groq/openai/gpt-oss-20b | 1 | - | - | 0 of 1 at 100 | 1 |
| multi_hop | groq/openai/gpt-oss-120b | 3 | 1 of 3 at 100 | 3 of 3 at 100 | 3 of 3 at 100 | 0 |
| multi_hop | groq/qwen/qwen3.8-27b | 3 | 2 of 3 at 100 | 2 of 3 at 100 | 3 of 3 at 100 | 1 |
| multi_hop | groq/openai/gpt-oss-20b | 3 | 2 of 3 at 100 | 3 of 3 at 100 | 3 of 3 at 100 | 0 |
| no_source | groq/openai/gpt-oss-120b | 1 | - | - | 1 of 1 at 100 | 0 |
| no_source | groq/qwen/qwen3.8-27b | 1 | - | - | 1 of 1 at 100 | 0 |
| no_source | groq/openai/gpt-oss-20b | 1 | - | - | 1 of 1 at 100 | 0 |
| personal_advice | groq/openai/gpt-oss-120b | 1 | - | - | 0 of 1 at 100 | 0 |
| personal_advice | groq/qwen/qwen3.8-27b | 1 | - | - | 1 of 1 at 100 | 0 |
| personal_advice | groq/openai/gpt-oss-20b | 1 | - | - | 0 of 1 at 100 | 0 |
| stale_premise | groq/openai/gpt-oss-120b | 2 | 2 of 2 at 100 | 2 of 2 at 100 | 2 of 2 at 100 | 0 |
| stale_premise | groq/qwen/qwen3.8-27b | 2 | 1 of 2 at 100 | 1 of 2 at 100 | 2 of 2 at 100 | 1 |
| stale_premise | groq/openai/gpt-oss-20b | 2 | 1 of 2 at 100 | 2 of 2 at 100 | 2 of 2 at 100 | 0 |

Income-year check (reported, not scored): answers that state the case's `income_year`.

No income-year cases in scope.

## 7. Ranking and decision (AB-32, AB-43 to AB-50)

| Order | Model | Composite | Gates | Failing answers across runs |
|---|---|---|---|---|
| 1 | `groq/qwen/qwen3.8-27b` | 84.2 | fail | 3 |
| 2 | `groq/openai/gpt-oss-120b` | 83.0 | fail | 3 |
| 3 | `groq/openai/gpt-oss-20b` | 78.6 | fail | 3 |

**No candidate passes every gate. On this evidence none is fit for client use (AB-32). The order above is provisional.**

Net case margin of `groq/qwen/qwen3.8-27b` over `groq/openai/gpt-oss-120b` (AB-43, real at 3 or more):

| Dimension | Net margin |
|---|---|
| Accuracy | +0 |
| Citation | +0 |
| Refusal | +2 |

## 8. Cases needing an analyst read (AB-16)

None.

Cases where judge correctness differs by 2 or more between runs or models (AB-49 rule 3 read): EVAL-011, EVAL-014, EVAL-015.

Answers using comma-list or range citations such as `[1, 2]`, which the harness does not count (CB-8): 2. groq/qwen/qwen3.8-27b run 1 EVAL-001, groq/qwen/qwen3.8-27b run 1 EVAL-019
