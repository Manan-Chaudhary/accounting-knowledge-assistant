# Latency targets

Team 83, Alfa Focus Knowledge Assistant.
Drafted 2026-10-07 by Ronith Mugundakumar.
Surfaces: the chat request path from the moment a question reaches the server to the final answer event: `app/chainlit/chainlit_app.py`, `app/rag/` (embedder, retriever, generator), the LiteLLM proxy (`litellm/config.yaml`), and the streaming endpoint card R127 adds.

Defines measurable latency targets for the chat: time to first token (TTFT), total response time, a time budget for each stage of the request, and the method used to measure them (where timings are captured, test conditions, number of runs, how results are reported and when a run passes). Requirement IDs are `LT-n` and are stable, per the traceability rule in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10.

**Status: draft for team agreement.** The total response time gate is the existing one, P95 <= 8 s in [`EVALUATION.md`](EVALUATION.md) line 176, and this document does not relax it. The current baseline fails it by a wide margin (section 4). The main new target is time to first token, which streaming changes. Every other number in sections 5 and 6 is a proposal marked `[ASSUMED]` until Hayden (PM) agrees it. No latency figure has been agreed with the client: [`REQUIREMENTS.md`](REQUIREMENTS.md) NF-1 (line 244) deliberately left response time unnumbered until someone has watched a user.

Priorities are MoSCoW: **M** must, **S** should, **C** could.

## 1. Purpose and scope

Sprint 3 adds streaming (R127, R140), a reranker (R139) and a latency investigation (R110). Without a target, none of them can be judged: a reranker that adds a second, or a streaming endpoint whose first token still arrives after 20 seconds, would both count as done. This document sets the targets and the method before the timing code is written, so R110 measures against numbers that were fixed in advance.

**In scope:** server-side TTFT and total time for one chat question, per-stage budgets, warm and cold conditions, the measurement method, and the pass or fail rule.

**Out of scope:**

- Concurrent users and load. That is exploration E-7 in `docs/ITERATION-AND-EXPLORATION.md` (branch `docs/sprint3-priorities`). All targets here are for one user asking one question at a time.
- Choice of default model and provider quota. That is E-5 and the A/B criteria in card R132. This document only says how the chosen model is timed.
- Where per-query records are stored long term. That is E-2 (observability). Section 6 defines the fields, not the store.
- The stream event format and the loading, stop and error states. Those are R127 and R140, with citation handling during the stream in `docs/CITATION-RULES.md` CB-26 to CB-28 (branch `docs/citation-behaviour-rules`) and failure wording in [`REQUIREMENTS.md`](REQUIREMENTS.md) EC-12.
- Document upload and ingestion time.
- The bounded agentic multi-hop loop (up to 3 iterations) in [`RAG-DESIGN.md`](RAG-DESIGN.md) sections 5 and 7, which [`LLM-BACKEND-CANDIDATES.md`](LLM-BACKEND-CANDIDATES.md) line 11 treats as part of the 8 s budget. It is not built: `retrieve_hybrid` makes one pass (`app/rag/retriever.py` lines 296-346). If it is built, every extra iteration (planning call, embedding, retrieval) counts inside S1 to S5 of the same request and against the same TTFT and total targets. It gets no separate allowance.
- The 45 second generation timeout that `ITERATION-AND-EXPLORATION.md` F9 reports PR #65 adding. It is not on main. A request that reaches it has already failed LT-6 (30 s with no first token) and the 8 s gate, so it is an error-handling limit, not a latency target.

## 2. What exists today

| Component | Current state | Verified in |
|---|---|---|
| Chat entry point | `on_message` runs `generate_response` in a worker thread through `cl.make_async`, waits for the whole reply, then sends one `cl.Message`. | `app/chainlit/chainlit_app.py` lines 108-128 |
| Model in the chat | The settings list offers `gemini-3-8-flash`, `groq-gpt-oss-120b`, `openrouter-free`, `free-fallback`. The default is `gemini-3-8-flash`. | `app/chainlit/chainlit_app.py` lines 63-69, 115 |
| Retrieval | Hybrid: `retrieve_dense` (embeds the query, then a pgvector cosine query, k=10) and `retrieve_keyword` (Postgres full text, k=10) run one after the other, fused by RRF (k=60), top 6 kept. | `app/rag/retriever.py` lines 16-19, 296-346 |
| Query embedding | Remote call to `BAAI/bge-m3` through the Hugging Face `hf-inference` provider. No model is loaded in the app process, so there is no local model load at start-up. A new `InferenceClient` is built on every call. | `app/rag/embedder.py` lines 8-29 |
| Indexes | An IVFFlat index exists on `document_chunks.embedding`. No full-text index exists, so `retrieve_keyword` computes `to_tsvector` over chunk content at query time. | `app/db/schema.sql` lines 27-28, `app/rag/retriever.py` lines 170-178 |
| LLM call | OpenAI client against the LiteLLM proxy `/v1`, no `stream`, no `max_tokens`, temperature 0.2. Prior turns of the thread are included in the prompt. | `app/rag/generator.py` lines 176-193 |
| Streaming | `generate_response_stream` exists and yields content deltas, but nothing calls it. | `app/rag/generator.py` lines 200-266 |
| Proxy routing | Router `timeout: 30`, `num_retries: 2`, fallbacks `gemini-3-8-flash` to `openrouter-free` to `free-fallback`. Gemini `rpm: 15`; Groq `rpm: 30`, `tpm: 8000`. | `litellm/config.yaml` lines 1-36 |
| Process layout | App and LiteLLM proxy are separate containers, so every LLM call is an extra network hop. The app runs one `uvicorn` process. | `docker-compose.yml` lines 1-29, `Dockerfile` line 27 |
| Hosting | Render is named as the production host. The plan, region and whether the service sleeps when idle are not recorded in the repo. | `README.md` line 49, `docs/CLIENT-BRIEF.md` line 88 |
| Timing in the chat path | None. No timer, no per-request log of stage times. | `app/chainlit/chainlit_app.py`, `app/rag/` |
| Timing in the harness | `retrieval_latency_ms` (embedding plus SQL) and `generation_latency_ms` (whole non-streamed reply) with `time.perf_counter()`. The harness calls `litellm.completion` directly, not the proxy, and its retry sleep (`time.sleep`) sits inside the generation timer. No TTFT. | `app/evaluation/harness.py` lines 150-183, 445-469, 553-558 |
| Report percentiles | Nearest-rank: `ordered[ceil(pct/100 * n) - 1]`. | `scripts/evaluation_report.py` lines 18-25 |
| Existing targets | "P95 <= 8s", wall-clock from query to final token. Repeated as a constraint in `LLM-BACKEND-CANDIDATES.md`. The harness page shows whatever gate R118 sets. | `docs/EVALUATION.md` line 176, `docs/LLM-BACKEND-CANDIDATES.md` line 11, `docs/HARNESS-PAGE-REQUIREMENTS.md` HP-34 (branch `docs/harness-page-requirements`) |

Two facts shape everything below. First, the chat does not stream, so today TTFT and total time are the same number: the user sees the pending indicator (`frontend/src/pages/Chat.tsx` line 296) until the last token is generated. Second, no one has ever measured TTFT, or split embedding time from SQL time, in this codebase.

## 3. Request stages

Stages are named `S0` to `S6` so the budget table, the log fields and the R110 report use the same names.

| Stage | What it covers | Starts | Ends | In TTFT |
|---|---|---|---|---|
| S0 Platform wake | Render starting a sleeping service, cold only | Request sent by client | Request reaches the app | Cold only, not in the server gate |
| S1 Intake | Session, settings and history lookup, request parsing | Handler entry (`on_message`, or the R127 endpoint) | Retrieval starts | Yes |
| S2 Query embedding | `embed_text` call to Hugging Face | Before `embed_text` | Embedding returned | Yes |
| S3 Retrieval queries and fusion | Dense SQL, keyword SQL, RRF, context formatting | After S2 | Formatted context ready | Yes |
| S4 Reranking | Cross-encoder over the hybrid candidates (R139, not built) | After S3 candidates | Reranked top set ready | Yes |
| S5 LLM time to first token | Proxy hop, provider queueing, any model reasoning before visible text | Request sent to the proxy | First non-empty content delta received | Yes |
| S6 Generation and finalise | Remaining tokens, sources event, done event | First content delta received | Done event written | No |

Client-side network and rendering after the server writes an event are not part of the server gate (LT-27 covers how they are reported). With the planned reranker, S3 returns a larger candidate set (R139 suggests about 20) and S4 cuts it to the final few.

## 4. Measured baseline

All evidence below comes from the harness result files in `benchmarks/results/`. The figures in `docs/model_evaluation_report.md` (for example "sub-1.2s response latency") are not traceable to any results file and are not used.

Limits that apply to every row:

- Every run used dense-only retrieval with top 6. Hybrid retrieval was added on 2026-10-04 (commit 634f389), after the Groq runs, so no hybrid or reranker timing exists yet.
- The harness bypasses the LiteLLM proxy and the chat path, and does not stream, so none of these numbers is a TTFT.
- The machine and network the runs used are not recorded in the result files.
- `generation_latency_ms` includes the harness's own rate-limit sleeps. [`EVALUATION.md`](EVALUATION.md) lines 196 and 226 already say the Groq P95 "mostly measures throttling, not the model", and `README.md` line 272 says the harness "waits out rate limits".

| Measure | Source | n | Result |
|---|---|---|---|
| Retrieval (embedding plus dense SQL), all calls | All 7 files in `benchmarks/results/` | 86 | p50 644 ms, p95 21,660 ms, max 70,007 ms (nearest rank). 16 of 86 calls took over 5 s. |
| Retrieval, first call of each file | Same | 7 | 1,695 to 9,850 ms, every one above the p50. Consistent with a cold first call; the cause (Hugging Face or database) is not separable from these files. |
| Generation, gpt-oss-120b (Groq) | `groq-gpt-oss-120b_2026-09-29.jsonl` | 22 | p50 28.3 s overall (nearest rank). The 5 calls under 10 s took 1,342 to 6,842 ms. |
| Generation, gpt-oss-20b (Groq) | `groq-gpt-oss-20b_2026-10-01.jsonl` | 22 | 3 calls under 10 s: 1,329 to 5,837 ms. |
| Generation, qwen3.8-27b (Groq) | `groq-qwen3.8-27b_2026-10-01.jsonl` | 22 | 3 calls under 10 s: 1,189 to 9,870 ms. |
| Generation, Gemini 3.8 Flash | `sample_gemini_3_8_flash.jsonl`, `baseline_check.jsonl`, `dense.jsonl` | 18 | Fastest 3,504 ms; 8 of 18 under 10 s; 4 over 25 s. `dense.jsonl` also has 7 cases recorded as `provider_unavailable`. |
| Answer length | `groq-gpt-oss-120b_2026-09-29.jsonl`; `sample_gemini_3_8_flash.jsonl` | 22; 4 | gpt-oss-120b p50 471 characters, p95 1,356. Gemini p50 2,151 characters, from only 4 answers. |

What this supports:

- Warm retrieval in the typical case is well under a second, but spikes are frequent and unexplained. The 644 ms p50 is embedding plus the dense SQL query only. These runs had no keyword query, so it is not directly comparable to the S2 plus S3 budget in section 5.2, which covers both queries.
- Whole answers on Groq took 1.2 to 9.9 s in the 11 of 66 calls that finished under 10 s. Of the other 55 calls, 43 took 20.5 to 35.6 s, 5 took 10.7 to 18.0 s, and 7 took 39.7 to 227.5 s. `EVALUATION.md` attributes this tail to rate-limit waits rather than model speed.
- Gemini 3.8 Flash, the chat default, finished within 15 s in 11 of 18 calls. The other 7 took 18.1 to 210.7 s; the four slowest were 25.8, 49.4, 135.2 and 210.7 s, which may include retries.
- The baseline fails the 8 s P95 gate. The harness reports put total P50 at 29.4 to 32.0 s for the three Groq models (`benchmarks/reports/comparison_2026-10-01.md`), and the Gemini whole-reply time alone exceeded 8 s in 14 of 18 calls. Some of this is throttling, but even the fastest Gemini replies (3.5 to 4.6 s) leave little room for retrieval.
- Nothing here can say how much of any reply is time to first token.

## 5. Targets

All targets are server-side, warm, one user, single-turn, measured by the method in section 6. The LT-2 p95 is the existing agreed gate. Every other figure is `[ASSUMED]` until agreed.

### 5.1 End-to-end targets

| LT | P | Metric | p50 | p95 |
|---|---|---|---|---|
| LT-1 | M | TTFT, warm, streaming on: handler entry to the first token event written to the client. The main new target. `[ASSUMED]` | <= 2.5 s | <= 4.5 s |
| LT-2 | M | Total response time, warm: handler entry to the done event written to the client. The p95 is the gate in `EVALUATION.md` line 176, unchanged. The p50 is derived from the stage budgets in 5.2 and is `[ASSUMED]`. | <= 5 s | <= 8 s (gate) |
| LT-3 | S | Non-streaming fallback (R140 "chat still works if streaming is unavailable"): total time meets LT-2. TTFT is not reported for this path because it equals total time. | as LT-2 | as LT-2 |
| LT-4 | S | Cold process: the first request after the app process starts, or after the idle interval in LT-24. TTFT for every cold sample is <= 15 s, excluding S0. Reported separately and never mixed into the LT-1 sample. | n/a | max <= 15 s |
| LT-5 | C | Platform wake (S0) is measured and reported, with no target until open question 2 is answered. | report | report |
| LT-6 | M | A request with no first token 30 s after handler entry is a failure. It stays in the percentile sample at its actual elapsed time, and counts towards the failure rate in LT-30. | n/a | n/a |

Rationale:

- **LT-1, 2.5 s / 4.5 s.** The users are accountants checking a rule mid-task, and [`REQUIREMENTS.md`](REQUIREMENTS.md) line 28 says answers "must be fast and skimmable". Once text starts arriving the user is reading rather than waiting, so TTFT is the number that decides whether they switch tasks (NF-1), and it is the number streaming improves. The value is the sum of the stage budgets in 5.2: a retrieval allowance near the measured warm p50 of 644 ms, a reranker, and an LLM first-token allowance that has not been measured for any model (LT-11). The target is set for the free tier the team uses, not for a paid one.
- **LT-2, p95 8 s.** This is the gate already agreed in `EVALUATION.md` line 176 and quoted in `LLM-BACKEND-CANDIDATES.md` line 11, and it stays authoritative. The current baseline fails it (section 4): Groq totals have a P50 near 30 s, and Gemini 3.8 Flash, the chat default, finished a whole reply within 15 s in only 11 of 18 calls. Meeting it needs throttling removed, a faster or shorter-answering configuration, or both; that is what R110 and the model choice (R132, E-5) have to show. Streaming does not change total time, so it cannot by itself make the gate pass. The p50 of 5 s is not an existing figure; it is the sum of the p50 stage budgets and is `[ASSUMED]`.
- **LT-33, a possible fallback.** See 5.3. A p95 of 15 s is offered only as a proposal Hayden may choose to adopt; it is not the gate.
- **LT-4, 15 s.** The slowest measured first call of a run spent 9,850 ms in retrieval alone. Adding the LLM first-token budget (2.4 s) gives about 12.3 s; 15 s leaves a margin without making the cold path a second normal path.
- **LT-6, 30 s.** Matches the LiteLLM router `timeout: 30` (`litellm/config.yaml` line 29). The proxy can keep trying after that (2 retries, then a fallback chain), so a user may still get an answer later, but for measurement a request that has shown nothing for 30 s has failed the user. Reconciling the proxy timeout with any app-level timeout is I-1 in `ITERATION-AND-EXPLORATION.md`, not this document.

### 5.2 Stage budgets

The budgets add up exactly to LT-1 and LT-2. Percentiles of separate stages do not add, so the budgets are diagnostic allocations: pass or fail is decided on the end-to-end metrics (LT-30), and a stage over its budget is a finding that points R110 at what to optimise.

| LT | P | Stage | p50 | p95 | Basis |
|---|---|---|---|---|---|
| LT-7 | S | S1 Intake | 50 ms | 100 ms | No I/O beyond the session store. `[ASSUMED]`, no measurement exists. |
| LT-8 | M | S2 Query embedding | 450 ms | 900 ms | Most of the measured 644 ms p50 (embedding plus the dense query only, no keyword query) is assumed to be the remote embedding call. R110 confirms the split. |
| LT-9 | M | S3 Retrieval queries and fusion | 300 ms | 500 ms | Two SQL queries run one after the other plus RRF. The keyword query has no full-text index, so this budget is the one most at risk as the corpus grows. |
| LT-10 | M | S4 Reranking | 300 ms | 600 ms | No measurement. Sized so the reranker costs less than the LLM first-token allowance. [`RAG-DESIGN.md`](RAG-DESIGN.md) line 177 says to revisit the cross-encoder if "Latency budget is blown"; this row is that budget. |
| LT-11 | M | S5 LLM time to first token | 1,400 ms | 2,400 ms | Unsupported until R110 measures it. The only evidence is the fastest Groq whole replies (about 1.2 to 1.4 s), which bound TTFT for those calls. The gating model is Gemini 3.8 Flash, whose TTFT is unknown and whose fastest whole reply was 3.5 s. `[ASSUMED]` |
| | | **Sum: TTFT (LT-1)** | **2,500 ms** | **4,500 ms** | |
| LT-12 | M | S6 Generation and finalise | 2,500 ms | 3,500 ms | What is left of LT-2 after the TTFT budget. No measured Gemini reply fits it: 14 of 18 whole replies took over 8 s. Groq replies under 10 s (1.2 to 9.9 s) show it is possible for short answers. Depends on answer length, so output size is logged (LT-19). |
| | | **Sum: total (LT-2)** | **5,000 ms** | **8,000 ms** | |

| LT | P | Requirement |
|---|---|---|
| LT-13 | M | Any stage whose p95 exceeds its budget is listed in the R110 report as a finding, even when LT-1 and LT-2 pass. When an end-to-end target fails, the report names the stage or stages over budget. |
| LT-14 | S | For the retrieval comparison in R111, the retrieval share of the budget is S2 + S3 = 750 ms p50 / 1,400 ms p95 without the reranker, and S2 + S3 + S4 = 1,050 ms / 2,000 ms with it. |

### 5.3 Relation to existing targets

| Existing | What it says | Relation | Which wins |
|---|---|---|---|
| [`EVALUATION.md`](EVALUATION.md) line 176 | P95 <= 8s, query to final token | LT-2's p95 is this gate, unchanged. LT-1 (TTFT) and the LT-2 p50 are added, not substituted. | `EVALUATION.md` wins. Nothing here relaxes it. |
| [`LLM-BACKEND-CANDIDATES.md`](LLM-BACKEND-CANDIDATES.md) line 11 | Quotes the same 8 s gate, including the multi-hop loop | Consistent. Section 1 says how a future multi-hop loop is counted. | `EVALUATION.md` wins. |
| [`REQUIREMENTS.md`](REQUIREMENTS.md) NF-1 | Not a number until a user has been observed | LT-1 is the interim number NF-1 asked to defer. It does not close NF-1. | NF-1 stands. Open question 1 tests these targets against a real user. |
| `HARNESS-PAGE-REQUIREMENTS.md` HP-34 | Shows the R118 gate if one is set | Consistent | HP-34 shows LT-2's p95 of 8 s, since the harness does not stream. |

| LT | P | Requirement |
|---|---|---|
| LT-33 | C | Proposal only, not a gate: if Hayden decides the 8 s P95 cannot be met on the free tier this sprint, he may adopt a total-time p95 of 15 s for the streaming chat, on the reasoning that with streaming the tail of a long answer is read while it arrives. Under it, LT-12's p95 would become 10,500 ms and the stage sums would still hold. Adopting it means changing `EVALUATION.md` line 176 first; until then, every report judges total time against 8 s. `[ASSUMED]` |

## 6. Measurement method

### 6.1 Where timings are captured

| LT | P | Requirement |
|---|---|---|
| LT-15 | M | Timings are taken on the server with a monotonic clock (`time.perf_counter()`, as the harness already uses), never wall-clock time and never only in the browser. Each request writes one structured log line (JSON) with a `request_id` and the fields in LT-16, LT-18 and LT-19. |
| LT-16 | M | Timer boundaries, in milliseconds: `intake_ms` handler entry to retrieval start; `embed_ms` around `embed_text` (called inside `retrieve_dense`, `app/rag/retriever.py` line 90); `retrieval_sql_ms` from embedding returned to formatted context ready, covering both queries, RRF and formatting; `rerank_ms` around the R139 reranker call; `llm_ttft_ms` from just before `chat.completions.create(stream=True)` to the first chunk with non-empty `delta.content` (the condition at `app/rag/generator.py` line 258); `ttft_ms` handler entry to the first token event written; `total_ms` handler entry to the done event written. Field names are `[ASSUMED]`; R110 may rename them but keeps one field per stage. |
| LT-17 | M | `ttft_ms` is taken when the first token event is written to the response, not when the provider chunk arrives. Both are recorded, so the gap between them (server buffering) is visible. |
| LT-18 | M | Each record carries the configuration: model requested, model actually used (the stream response `model`, which `generator.py` lines 248-249 already print), retrieval strategy, final top k, candidate k, reranker on or off, streaming on or off, git commit, and a `cold` flag (true for the first request after process start or after the idle interval). |
| LT-19 | S | Each record carries answer length (output tokens where the provider returns usage, otherwise characters), so a slow S6 can be split into a long answer or a slow provider. |
| LT-20 | M | Provider retry and rate-limit sleeps never sit inside a stage timer used for these targets. The harness's `complete_with_retry` sleep (`app/evaluation/harness.py` line 181) is inside its generation timer today; if R110 uses the harness, it times only the successful attempt and records the retry count, or the request is excluded and counted as a failure. |

### 6.2 Test conditions

| LT | P | Requirement |
|---|---|---|
| LT-21 | M | The gating run is against the deployed environment, through the R127 streaming endpoint, so it uses the same proxy, database, embedding provider and model as users. A client script sends one question at a time and waits for the done event. Local runs are for diagnosis and never used to claim a pass. Before R127 lands, R110 may measure S5 locally with the unused `generate_response_stream`, reported as a local result. |
| LT-22 | M | The gating configuration is the chat's default model at the time of the run (today `gemini-3-8-flash`), with the deployed retrieval settings. Any other model or setting is a separate configuration with its own result. |
| LT-23 | M | Question set: all 22 cases in `benchmarks/questions.jsonl` (C1 10, C3 2, C4 4, C5 1, C6 3, C7 2). Each question is sent as the first message of a new thread, so history does not change prompt size between runs. |
| LT-24 | M | Warm-up: after a deploy, or after 15 minutes with no request `[ASSUMED]`, the first 2 requests are discarded from the warm sample and recorded as cold samples for LT-4. |
| LT-25 | M | Number of runs: 3 passes over the 22 questions, giving 66 warm samples per configuration. Percentiles use the nearest-rank method of `scripts/evaluation_report.py` lines 18-25, so p50 is the 33rd and p95 the 63rd smallest of 66. A run with fewer samples is reported as indicative, not as a pass. |
| LT-26 | M | Requests are spaced so the run stays inside the limits in `litellm/config.yaml` (Gemini `rpm: 15`; Groq `rpm: 30`, `tpm: 8000`). The Gemini 3.8 Flash free tier is taken to allow about 20 requests a day `[ASSUMED]`. That figure comes from `EVALUATION.md` line 227 and `ITERATION-AND-EXPLORATION.md` E-5, neither of which cites a Google source, and `LLM-BACKEND-CANDIDATES.md` line 22 lists 1,500 requests a day for a different model (`gemini-2.5-flash`). On the 20 a day figure, with 2 warm-up requests discarded each day, 66 samples take at least 4 days (18 per day). The run either uses a paid key or is split across days with LT-24 applied each day, and the report states which and the quota observed. |
| LT-27 | S | The report records where the client ran and on what connection. Client-observed TTFT (from the script, or from the browser for R140) is reported next to the server figure but does not decide pass or fail. |
| LT-28 | S | Results are also broken down by class, at least C1 (single fact) against C4 (multi-hop) and the refusal classes C6 and C7, whose answers are shorter. |

### 6.3 Reporting and pass or fail

| LT | P | Requirement |
|---|---|---|
| LT-29 | M | The report has: a configuration block (LT-18 fields, date, environment, client location); a stage table with n, p50, p95, max, budget and count over budget for each of S1 to S6; TTFT and total against LT-1 and LT-2; the cold samples against LT-4; and every failure with its error. |
| LT-30 | M | A configuration passes when, over at least 66 warm samples, TTFT p50 and p95 meet LT-1, total p95 meets the 8 s gate in LT-2, and no more than 5% of requests fail (3 of 66) under LT-6. Failed requests are never dropped from the percentile sample. Total p50 against LT-2's 5 s is reported, and a miss is a finding rather than a fail until that figure is agreed. |
| LT-31 | M | The per-request records are saved as JSONL under `benchmarks/results/` and the report under `benchmarks/reports/`, so every figure can be traced to a file. |
| LT-32 | S | The method is re-run before a latency improvement is claimed and whenever the default model, retrieval depth, reranker or system prompt changes, in line with NF-4. |

## 7. Card checklist coverage

| R118 checklist item | Covered by |
|---|---|
| Time budget per stage defined (retrieval, reranking, LLM) | Section 3, LT-7 to LT-14 |
| Target for time to first token defined | LT-1, LT-4 |
| Rationale for each target recorded | Section 4, rationale under 5.1, basis column in 5.2, section 5.3 |
| Target for total response time defined | LT-2 (existing 8 s P95 gate), LT-3, LT-6, LT-33 (non-gating proposal) |
| Measurement method defined (where timings are captured, test conditions, number of runs) | LT-15 to LT-32 |

## 8. Open questions

| # | Question | For | Affects |
|---|---|---|---|
| 1 | Is about 2.5 seconds to the first words, with most complete answers within 5 seconds and nearly all within 8, acceptable for staff checking a rule mid-task? Best answered by watching one user, as NF-1 asks. | Client | LT-1, LT-2 |
| 8 | If R110 shows the 8 s P95 cannot be met on the free tier this sprint, does the team pay for a provider, shorten answers, or adopt LT-33 by changing `EVALUATION.md`? | Team (Hayden) | LT-2, LT-33 |
| 2 | Is the deployed Render service on a plan that sleeps when idle, and how long does it take to wake? | Team (Hayden) | LT-5, LT-24 |
| 3 | Which model is the gating configuration for Sprint 3? | Team, via E-5 and R132 | LT-22 |
| 4 | Paid key or a run split across days for the measurement quota? | Team (Hayden) | LT-26 |
| 5 | Does the reranker run in the app process on Render's CPU, or as a hosted API? | Shihong, R139 | LT-10 |
| 6 | In production, does the LiteLLM proxy run on the same host as the app? | Team | LT-11 |
| 7 | Should answers have a token cap? `generate_response` sets none today. PR #65 proposed 1,200 tokens (`ITERATION-AND-EXPLORATION.md` F9), which is not on main. | Team | LT-12 |

## 9. Handoff: who uses this next

- **R110, Hayden Nguyen (latency breakdown):** runs section 6 (LT-15 to LT-31) and reports against LT-1, the 8 s P95 gate in LT-2 and the stage budgets LT-7 to LT-12. Expect the baseline to fail the gate (section 4). The first questions to answer are Gemini's actual TTFT (LT-11 is unsupported until then) and whether the retrieval spikes come from S2 (Hugging Face) or S3 (database).
- **R127, Zekun Liu (streaming endpoint):** places the timers in LT-16 and LT-17 in the endpoint, writes the LT-15 log line, and keeps the S1 to S6 boundaries visible in code.
- **R140, Zekun Liu (streaming frontend):** LT-3 for the non-streaming fallback; the cold and wake cases (LT-4, LT-5) need the loading state to hold for up to 15 s without looking broken.
- **R126, Shihong He (test streaming):** checks that TTFT is recorded per LT-16 and LT-17 and that the first token event arrives before the done event. A smoke test of a few questions reports TTFT as indicative only (LT-25).
- **R139, Shihong He (reranker):** documents its added latency as `rerank_ms` against LT-10, with the candidate count it used.
- **R111, Hayden Nguyen (test hybrid and reranker):** records S2, S3 and S4 for vector-only, hybrid and hybrid with reranker against LT-14.
- **R132, Ronith Mugundakumar (A/B scoring):** uses LT-1 and the 8 s P95 gate in LT-2 as the latency thresholds for the latency dimension.
- **Hayden (PM):** agrees or changes the `[ASSUMED]` figures in section 5 (LT-1, the LT-2 p50, the stage budgets). The 8 s gate stays as it is unless he chooses LT-33, which needs `EVALUATION.md` line 176 changed first (open question 8).
