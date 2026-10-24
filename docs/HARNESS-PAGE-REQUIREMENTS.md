# Evaluation harness page requirements

Team 83, Alfa Focus Knowledge Assistant.
Drafted 2026-10-07 by Ronith Mugundakumar.
Surfaces: the run controls, progress, results and run history on the LLM Testing & Evaluation page (`/testing`, `frontend/src/pages/Testing.tsx`), and the backend that runs `app/evaluation/harness.py` on its behalf.

Defines how the existing evaluation harness is run from the page instead of the console: who may run it, how the test set, model and settings are chosen, how a run starts, shows progress, is stopped and resumed, which metrics are shown against which gates, what each per-question result shows, how runs are stored and compared, and what happens when a run fails. Requirement IDs are `HP-n` and are stable, per the traceability rule in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10.

**Status: partially implemented.** Built: team-only access enforced on server and browser (HP-1 to HP-4), start, one run at a time (409, HP-22 in part), background run with live progress (HP-20, HP-26), stop (HP-28 in part), settings for test set, model, strategy, depth and judge (HP-15, HP-17 in part), and summary metrics with gate verdicts and "not implemented" planned metrics (section 7 in part, HP-33, HP-36 in part). Not built: run and queue persistence, history, comparison, per-question results, class filter, resume, interrupted-run detection, provider-failure auto-stop, key-availability checks, export, per-class metric breakdown, and reviewer access. Differences from section 7: judge correctness and faithfulness are shown as informational cards (as HP-35 asks), but the cards show Recall@K as a gated metric (95%) where this document lists it report-only, and omit the source-hit proxies and top-1 precision. Run state is in memory only. Requirements marked `[ASSUMED]` are proposals that need team or client confirmation before they drive a build. The largest is the gate treatment of judge-scored metrics in section 7, which follows from the judge being unvalidated.

This document does not restate [`TESTING-PAGE-REQUIREMENTS.md`](TESTING-PAGE-REQUIREMENTS.md). EV-n already governs what one evaluation record holds, the scoring fields, model comparison, labelling, outcomes, aggregation, gates and access. Where an EV requirement covers something, this document points to it. Where the harness as written conflicts with an EV requirement, section 12 says so and states which wins.

Priorities are MoSCoW: **M** must, **S** should, **C** could.

## 1. Purpose and scope

When this was written the page was a static mockup with no backend. It is now a working run-and-summary page (section 2); the rest of this document still describes the larger target. Every number in [`EVALUATION.md`](EVALUATION.md) section 4.2 came from someone running `scripts/run_evaluation.py` on a laptop. This document defines the layer between the two, so the team can run the benchmark from the browser and the result can be traced from the page back to the answer that produced it.

**In scope:** run permissions, test set and model selection, run settings, starting a run, concurrent run requests, live progress, cancel, resume after interruption, the summary metrics and their gates, the per-question result row, run storage and history, run comparison, and run failure states.

**Out of scope:**

- The evaluation record schema, scoring fields and outcome states. EV-1 to EV-6 and EV-30 to EV-33.
- Human labelling, blinded review, disagreement and adjudication. EV-21 to EV-23, EV-34 to EV-36.
- Reviewer model preference and wins, losses and ties. EV-26 to EV-29.
- New metrics (temporal precision, citation support, corpus attribution). They are scorer work in `app/evaluation/harness.py` and [`EVALUATION.md`](EVALUATION.md) section 5. This page shows them once they exist (HP-38).
- Editing benchmark questions from the browser. Questions stay in version control per [`EVALUATION.md`](EVALUATION.md) section 3.
- Latency targets. Those are card R118; HP-34 shows whatever gate that card sets.

## 2. What exists today

Checked against `main` on 2026-10-22.

| Component | Current state | Verified in |
|---|---|---|
| Testing page | **Built (reduced scope).** The page loads settings from `GET /api/testing/config`, starts a run, polls it every 1.2 seconds, offers Stop, restores an active run on reload, and shows run progress (completed, passed, failed, remaining, elapsed, current case) and summary metric cards with gate verdicts. Settings: test set, model, retrieval strategy, top-k, optional judge model. A "Planned metrics" strip lists Temporal Precision, Citation Support, Corpus Attribution and Cost Per Query as not implemented. A note on the page says per-question inspection is outside this ticket. Not built: run history, comparison, per-question rows, class filter, resume, queue, export. | `frontend/src/pages/Testing.tsx` |
| Page access | `/testing` is wrapped in `RequireAuth` and `RequireTeam`. `RequireTeam` redirects anyone whose role is not `team` to `/home`. The server also enforces it: every `/api/testing` handler calls `_require_team` (401 without a session, 403 for any role other than `team`). | `frontend/src/App.tsx`; `frontend/src/auth/RequireTeam.tsx`; `app/routes/testing.py` |
| Backend route | **Built.** `GET /api/testing/config`, `GET /api/testing/runs/active`, `POST /api/testing/runs` (202), `GET /api/testing/runs/{id}`, `POST /api/testing/runs/{id}/stop`. A run is a subprocess (`python -m scripts.run_evaluation`) writing its own JSONL file under a temp directory, with a monitor thread. One run at a time: a second start returns 409. Run state is held in process memory only, so a server restart loses it, and result files live in the OS temp directory. | `app/routes/testing.py` |
| API guard | Middleware returns 401 for any unauthenticated `/api/` call. It checks authentication only; role is checked in the testing handlers. Any path containing `/chat` is treated as public. | `app/main.py` `enforce_authenticated_access`; `app/routes/testing.py` |
| Roles | `app_users.role` is `staff`, `admin` or `team`. There is no reviewer role. | `app/db/models.py` |
| Run storage | `eval_results` table exists with `question`, `expected_answer`, `model_name`, `model_answer`, `accuracy_score`, `latency_ms`, `cost_usd`, `created_at`. Nothing writes to it. The page's runs are not stored in the database: results are JSONL files in a temp directory plus in-memory state. | `app/db/models.py`; `app/db/schema.sql`; `app/routes/testing.py` |
| Harness runner | `run_suite` loads a JSONL test set, runs each case through retrieval, generation and optional judge, and appends each result to a JSONL file as it completes. | `app/evaluation/harness.py` |
| Console entry | `scripts/run_evaluation.py` takes `--questions`, `--output`, `--model`, `--top-k`, `--strategy`, `--judge`, `--report`, `--resume`. The page uses all except `--report` and `--resume`. | `scripts/run_evaluation.py`; `app/routes/testing.py` `_build_command` |
| Report | `summarise`, `case_failures` and `build_report` aggregate result files. The page backend calls `summarise` and `case_failures` to build the metric cards. | `scripts/evaluation_report.py`; `app/routes/testing.py` `_build_summary` |
| Test sets | One set is offered, `core-mvp` = `benchmarks/questions.jsonl`: 50 cases (classes C1 18, C2 7, C3 4, C4 6, C5 1, C6 11, C7 3), 14 must-refuse. The 22-case set that sections 2.1 and 13 refer to is the earlier version. `benchmarks/questions.md` is prose, not a runnable set. | `benchmarks/questions.jsonl`; `app/routes/testing.py` `TEST_SETS` |
| Models offered | A fixed list of LiteLLM proxy aliases: `gemini-3-8-flash`, `groq-gpt-oss-120b`, `openrouter-free`, `free-fallback`. Not tied to provider-key checks (HP-12 is not built). | `app/routes/testing.py` `MODEL_OPTIONS` |
| Model calls | The harness now calls the LiteLLM proxy (`litellm_proxy/{model}` with `api_base` from `LITELLM_PROXY_URL` and `LITELLM_MASTER_KEY`), so proxy fallbacks apply. This reverses the earlier direct-provider behaviour (open question 1, HP-61): a fallback can attribute one model's answers to another, and the page does not flag it. | `app/evaluation/harness.py`; `litellm/config.yaml` |
| Tests | `tests/evaluation/test_harness.py`, `test_report.py` and `test_testing_api.py`. | `tests/evaluation/` |

### 2.1 How long a run takes, and how it fails

Measured from the `created_at` of the first and last saved case in each result file. The first stamp is written after the first case finishes, so true run time is slightly longer.

| Result file | Cases saved | First to last case | Notes |
|---|---|---|---|
| `groq-gpt-oss-120b_2026-09-29.jsonl` | 22, all `ok` | 17 min | One run id |
| `groq-qwen3.8-27b_2026-10-01.jsonl` | 22, all `ok` | 19 min | One run id |
| `groq-gpt-oss-20b_2026-10-01.jsonl` | 22, all `ok` | 13 min | Two run ids (5 + 17), so resumed once |
| `dense.jsonl` (Gemini 3.8 Flash), first call | 12, all `ok` | 12 min | Run id `88ee4d199889`, 03:11 to 03:23 UTC on 2026-10-04 |
| `dense.jsonl`, second call | 7, all `provider_unavailable` | 23 min | Run id `cc8d0a98da63`, started after an 88.5 min idle gap. Each case failed with a 429 `RateLimitError`, about 3.8 min apart. Cases EVAL-020 to EVAL-022 were never saved |

The `dense.jsonl` file spans 2 h 3 min, but about 35 min of that is active running; the rest is the idle gap between the two calls. The 3.8 min per failed case is the harness working through 6 attempts with backoff before recording the failure. It is the evidence for HP-31: once a daily quota is gone, every further case costs nearly 4 minutes and produces nothing.

Run ids in these files are not run identities. `run_suite` creates a new `run_id` on every call, including a resume, so a resumed file holds two ids for one logical run. HP-62 deals with this.

[`EVALUATION.md`](EVALUATION.md) section 4.2 records the Gemini free tier at 20 requests per day for that model. A full run makes 22 generation calls, plus up to 16 judge calls when a judge is set, plus any retries. One run can exhaust a daily quota on its own. The page has to treat a long, partly failed run as the normal case, not the exception.

### 2.2 The reuse seam

The card requires the existing evaluation script to be reused, not rewritten. These are the functions the page backend calls. The page computes no metric itself.

| Function | File | What the page uses it for |
|---|---|---|
| `load_cases(path)` | `app/evaluation/harness.py` | Validate a test set and count its cases before a run starts |
| `run_suite(questions_path, output_path, model, top_k, judge_model, resume, retrieval_strategy)` | `app/evaluation/harness.py` | Execute a run, and resume one |
| `RETRIEVAL_STRATEGIES`, `DEFAULT_MODEL`, `DEFAULT_TOP_K`, `DEFAULT_RETRIEVAL_STRATEGY` | `app/evaluation/harness.py` | Populate the settings controls and their defaults |
| `api_key_for(model)` | `app/evaluation/harness.py` | Check a provider key is configured before starting |
| `rescore(result)` | `app/evaluation/harness.py` | Re-apply deterministic scoring to a stored run, under HP-45 |
| `summarise(results)`, `refusal_scores(results)` | `scripts/evaluation_report.py` | Summary metrics, overall and per class |
| `case_failures(result)` | `scripts/evaluation_report.py` | The failure reasons on each per-question row |
| `build_report`, `write_report` | `scripts/evaluation_report.py` | Comparison table and export |

## 3. Who can run the harness

| ID | P | Requirement |
|---|---|---|
| HP-1 | M | Only accounts with role `team` can start, cancel, resume or delete a run, or see the run controls. This follows AU-3 and EV-49, which limit `/testing` to Team 83 plus the validation reviewers (see HP-6 for what reviewers get), and AU-10, which makes Team 83 accounts distinguishable by role. |
| HP-2 | M | The role check runs on the server for every harness endpoint, using the role from the server's session record per AU-40. A request from a `staff` or `admin` account returns 403 and starts nothing. `RequireTeam` in the browser is not the control. |
| HP-3 | M | An unauthenticated call to any harness endpoint returns 401. This holds today through the middleware (AU-85) and must keep holding. |
| HP-4 | M | No harness endpoint path contains the string `/chat`. The middleware treats any such path as public (`enforce_authenticated_access` in `app/main.py`), so a path like `/api/testing/runs/1/chat` would skip authentication. |
| HP-5 | M | `admin` accounts cannot run the harness. Running costs shared provider quota and is a development task, not firm administration. `[ASSUMED]` |
| HP-6 | S | Validation reviewer accounts (EV-49) can open the labelling view defined by EV-22 but never see run controls, settings, model names or scores. No reviewer role exists in code, and a reviewer must not be given `team` to get in, because `team` exposes everything EV-22 and EV-25 hide. See open question 2. |

## 4. Choosing what to run

| ID | P | Requirement |
|---|---|---|
| HP-7 | M | The test set is chosen from a list of the `.jsonl` files in `benchmarks/`. Today that list has one entry, `questions.jsonl`. Free-text paths are not accepted. Upload of a test set from the browser is not offered, because of EV-50. `[ASSUMED]` that the list is read from the deployed repository rather than the database. |
| HP-8 | M | Before a run can start, the selected set is loaded with `load_cases`. A set that fails to load (a case missing `id` or `question`, or invalid JSON) shows the loader's error message with the line or case id, and the Run control stays disabled. |
| HP-9 | M | Once a set is loaded, the page shows its case count, the count per class, the must-refuse count, and the count with an `expected_answer` (the cases the judge can score). |
| HP-10 | S | The user can limit a run to one or more classes, per [`EVALUATION.md`](EVALUATION.md) section 6 ("all classes, or one class"). The backend writes the filtered cases to a new JSONL file and passes that to `run_suite`, so the harness itself is unchanged. The run records which classes were included. |
| HP-11 | M | The model is chosen from a configured list, not typed. Each entry is a LiteLLM model string the harness accepts (`provider/model`, for example `groq/openai/gpt-oss-120b`, as used in the existing result files). The list is shared with card R137, which adds the candidate models. |
| HP-12 | M | A model whose provider key is not configured (`api_key_for` returns nothing) is shown as unavailable and cannot be started. The message names the missing setting (`GEMINI_API_KEY`, `GROQ_API_KEY` or `OPENAI_API_KEY`) and never shows a key value. |
| HP-13 | M | One run evaluates one model, because `run_suite` takes one model. Comparing models means running each with identical settings and comparing the runs (section 10). |
| HP-14 | S | The user can select several models at once. The page queues one run per model with identical settings and runs them one after another, grouped so they open together in the comparison view. This is how R100 runs more than five models without five manual starts. |
| HP-15 | M | The judge is chosen from the same model list, or set to none. With none, correctness and faithfulness are shown as not measured, not as zero. |
| HP-16 | S | When the judge is the same model as the candidate, the page labels the run's judged scores as self-judged. [`EVALUATION.md`](EVALUATION.md) section 4.2 records this for gpt-oss-120b. |
| HP-17 | M | Retrieval strategy is chosen from `RETRIEVAL_STRATEGIES` (dense, keyword, hybrid), default `hybrid`. Retrieval depth (`top_k`) is a whole number above zero (the API caps it at 20), default `DEFAULT_TOP_K` (6 in the harness; the chat retriever default is 5). Defaults are read from the harness constants, not copied into the frontend. |
| HP-18 | S | The settings panel states which depth the deployed assistant uses, so a run at a different depth is a deliberate choice. The chat retriever's `DEFAULT_TOP_K` is 5 while the harness default is 6, so a default run does not match the deployed depth. See open question 3. |
| HP-19 | S | Before start, the page shows the planned number of model calls (cases, plus judged cases when a judge is set) next to the chosen model, so a user can see when a run will exceed a free-tier daily limit. Known limits per provider come from exploration E-5. `[ASSUMED]` |

## 5. Starting a run and concurrent requests

| ID | P | Requirement |
|---|---|---|
| HP-20 | M | Starting a run returns a run id at once and runs the harness in the background. The user does not have to keep the page open; closing the tab does not stop the run, and reopening the page shows its current state. A 22-case run takes 13 to 19 minutes on the Groq free tier (section 2.1). |
| HP-21 | M | Each run writes to its own result file, named from its run id. A run never writes to a file another run uses. `run_suite` truncates its output file on a fresh start, so a shared path, such as the console default `sample_results.jsonl`, destroys the earlier run. |
| HP-22 | M | Only one run executes at a time across the deployment. Concurrent runs share provider quota, slow each other, and inflate each other's latency. `[ASSUMED]` |
| HP-23 | M | A start request while a run is executing is not rejected silently. Under HP-14 it is queued and the page shows its place in the queue. Otherwise the server returns 409 and the page names the running run, who started it, and its progress. |
| HP-24 | M | Two start requests arriving together cannot both start. The check for an executing run and the creation of the new run are one atomic step on the server. |
| HP-25 | S | A queued run can be removed from the queue by any `team` account before it starts. |

## 6. Progress, cancel and resume

| ID | P | Requirement |
|---|---|---|
| HP-26 | M | While a run executes, the page shows cases completed out of cases planned, the id of the case in progress, elapsed time, and counts so far of `ok` and `provider_unavailable` cases. Progress updates at least every 10 seconds without a manual refresh. `[ASSUMED]` interval. |
| HP-27 | S | When the harness is waiting on a provider retry (`complete_with_retry`, up to 6 attempts), the page says it is waiting on the provider and for how long, so a rate-limit pause is not read as a hang. |
| HP-28 | M | Any `team` account can cancel an executing run. Cancelled runs keep every case already saved. At most the case in progress is lost. The run is marked `cancelled` with who cancelled it and when. |
| HP-29 | M | A run that stopped before all cases were saved (cancelled, failed, interrupted, or stopped under HP-31) can be resumed. Resume calls `run_suite` with `resume=True` on the same result file, which keeps saved cases without an error and reruns missing and failed ones. |
| HP-30 | M | Resume uses exactly the settings of the original run: test set and its content hash, classes, model, judge, strategy and depth. The page offers no setting changes on resume. `run_suite` does not check this itself, so mixing models in one result file is otherwise possible. |
| HP-31 | S | A run stops itself after 3 consecutive `provider_unavailable` cases and is marked `stopped: provider unavailable`, resumable later. Without this, a run that exhausts a daily quota spends up to 6 retries on every remaining case before recording each as failed, as `dense.jsonl` shows. `[ASSUMED]` threshold of 3. |
| HP-32 | M | A run with no case saved for 15 minutes is marked `interrupted`, including after a host restart that killed it, and is resumable. A run is never shown as running indefinitely. `[ASSUMED]` 15 minutes, above the longest retry sequence the harness can wait through without a provider hint. |

Resume is not a re-run. EV-5 says a re-run creates a new run id. Resume completes the same run and keeps its id. Run Again on a finished run starts a new run with a new id and the same settings.

## 7. Metrics shown and their gates

The page shows the values `summarise` returns, against the gates in [`EVALUATION.md`](EVALUATION.md) section 4, with pass or fail resolved on the page (EV-42). Gate values are copied from that document, not set here. Retrieval and generation are grouped separately (EV-44) and every metric is also shown per class (EV-41).

| Group | Shown as | Harness source | Gate (EVALUATION.md section 4) | Page treatment |
|---|---|---|---|---|
| Retrieval | Recall@10 (proxy: source hit at k) | `expected_source_hit` rate | >= 0.95 | Pass or fail. Labelled proxy: source-file level and k is the run's depth, not 10 (EVALUATION.md 4.1) |
| Retrieval | Recall@k | `recall_at_k` average | none | Report only |
| Retrieval | Context precision (proxy: top-1 hit) | `top1_source_hit` rate | >= 0.70 | Pass or fail, labelled proxy |
| Retrieval | MRR | `reciprocal_rank` average | report | Report only |
| Retrieval | Temporal precision | not computed | >= 0.98 | Not measured |
| Retrieval | Corpus routing accuracy | not computed | >= 0.90 | Not measured |
| Generation | Citation resolution | `citation_valid` rate and `citation_format_standard` rate | 1.00 | Hard pass or fail on each (EV-43). Both map to this metric in EVALUATION.md 4.1. No URL check yet |
| Generation | Citation present (answerable cases) | `citation_present` rate | none | Report only `[ASSUMED]`. Missing citations still fail the case under `case_failures` |
| Generation | Citation support | not computed | >= 0.95 | Not measured |
| Generation | Correctness | `judge.correctness` average, 1 to 5 | >= 0.85 on a 0 to 1 scale | Report only `[ASSUMED]` |
| Generation | Faithfulness | `judge.faithfulness` average, 1 to 5 | >= 0.95 on a 0 to 1 scale | Report only `[ASSUMED]` |
| Generation | Answer relevancy, corpus attribution | not computed | >= 0.90, >= 0.95 | Not measured |
| Behavioural | Refusal recall | `refusal_recall` | >= 0.95 | Pass or fail. Labelled pattern-based (EVALUATION.md 4.1) |
| Behavioural | Refusal precision | `refusal_precision` | >= 0.85 | Pass or fail, shown next to recall, never alone |
| Behavioural | Refusal correct | `refusal_correct` rate | none | Report only |
| Behavioural | Stale-premise correction, income-year scoping | not computed | >= 0.90, >= 0.95 | Not measured |
| Operational | P50, P95 latency | `p50_latency_ms`, `p95_latency_ms` | P95 <= 8s | Pass or fail, labelled as including provider waits |
| Operational | Cost per query | not computed | report | Not measured |
| Run | Cases, provider failures | `cases`, `provider_failures` | none | Completeness figure per EV-32 |

| ID | P | Requirement |
|---|---|---|
| HP-33 | M | Every gated metric the harness computes is shown with its value, its gate and a pass or fail verdict, using the table above. The page computes nothing itself: values come from `summarise` over the run's stored records, and a run's numbers on the page equal the numbers `build_report` produces for the same result file. |
| HP-34 | M | Latency is shown against the P95 gate with a label that the harness timer includes provider retry and rate-limit waits (EVALUATION.md 4.1). If R118 sets a different latency target, the page uses that target. |
| HP-35 | M | Correctness and faithfulness are shown as report-only averages on their 1 to 5 scale, with no pass or fail, labelled "No gate on this scale". This departs from EV-42; section 12 records why. The gates are defined on a 0 to 1 scale with no agreed mapping, and EVALUATION.md section 5 says a judge not validated against human labels is not fit to gate anything. `[ASSUMED]` until judge validation (E-4) reports agreement. |
| HP-36 | M | A gated metric the harness does not compute is listed with its gate and the words "Not measured". It is never shown as pass, never left out, and never counted in a pass total. |
| HP-37 | M | The run summary states gates passed out of gates measured, and separately how many gated metrics are not measured. It never states that all gates pass while any gated metric is not measured. |
| HP-38 | S | When the harness gains a scorer for a metric listed as not measured, the page shows it against its gate with no page change beyond adding the field to the metric list. |
| HP-39 | M | A metric whose denominator is zero for the run (for example refusal recall on a class with no must-refuse case) shows "n/a", as `fmt` does today, not 0 and not a verdict. |
| HP-40 | M | Aggregates on a run that is not complete carry a partial label with cases saved out of planned, per EV-39. Provider-failed cases are excluded from quality denominators and counted separately, per EV-32, which `summarise` already does for every rate except `answer_returned`. |

## 8. Per-question results

What a row shows is set here. How rows compare across models is EV-24; filters are EV-47. The build is card R95.

| ID | P | Requirement |
|---|---|---|
| HP-41 | M | Every case in the run has one row: case id, class, question, expected sources, must-refuse flag, outcome, and pass or fail. A case fails when `case_failures` returns any reason, and the reasons are shown on the row in its words (for example "expected source not retrieved", "invalid citations [7]", "missed refusal", "over-refusal", "judge correctness 2/5"). |
| HP-42 | M | Expanding a row shows: the retrieved chunks in rank order with filename, source label, chunk index and similarity; each chunk's stored text; the generated answer as returned; every metric in the record's `metrics` object; the judge's correctness, faithfulness and reason, or the judge's error; retrieval, generation and total latency; and the `expected_outcome` and `expected_answer` from the test set. |
| HP-43 | M | A case recorded as `provider_unavailable` shows the stored error and is marked as an error outcome, not as a wrong answer (EV-32, EV-33). |
| HP-44 | M | Failed cases are visibly marked and can be filtered to on their own, and by failure reason. Results load from storage for a finished run without rerunning anything. |

## 9. Storage of runs

| ID | P | Requirement |
|---|---|---|
| HP-45 | M | Records are stored in the database, one per case per run, holding the fields EV-1 to EV-6 require. The harness record already supplies the question id, class, model, answer, ordered chunk ids with similarity scores, and timestamp. It does not supply these, which are new work and listed as gaps in section 12: EV-2 resolved income year and the `no_source` versus `refused` outcome split; EV-3 full chunk text; EV-4 scorer version or prompt hash; EV-6 prompt version and corpus snapshot id; and the error stage EV-32 asks for. Until each exists, its column is stored as not recorded, not guessed. The current `eval_results` table cannot hold them (section 2) and is replaced or migrated, not written to as is. The result JSONL file is the harness's working file, not the store of record. `[ASSUMED]` that files on the hosted instance do not survive a restart. |
| HP-46 | M | Each completed case reaches the database before the run is marked complete, and within one case of completion while the run executes, so a host restart loses at most the case in progress. |
| HP-47 | M | Each run has one run record: run id (the page's own key, per HP-62), who started it, start and end time, status (`queued`, `running`, `completed`, `cancelled`, `failed`, `interrupted`, `stopped: provider unavailable`), test set file name and content hash, classes included, model, judge, strategy, depth, cases planned, cases saved, `ok` count, `provider_unavailable` count, the run-level error if any, and who cancelled it if anyone. |
| HP-48 | S | The run record stores the commit of the deployed code, so a change in scoring between runs is visible. This is part of EV-6's pipeline configuration. |
| HP-49 | M | Re-scoring a stored run with `rescore` writes a new scored version linked to the original and leaves the original records unchanged (EV-5). The page never calls `write_report` with `rescore=True` on stored data, since that overwrites the source file (`scripts/evaluation_report.py`). |
| HP-50 | M | The run history lists every run, newest first, with status, model, test set, settings, start time, who started it, and cases saved out of planned. Failed, cancelled and interrupted runs stay in the list. |
| HP-51 | C | The three complete Groq runs in `benchmarks/results/` can be imported, so history starts with the runs [`EVALUATION.md`](EVALUATION.md) section 4.2 reports. They predate retrieval strategies, so their strategy is shown as not recorded. |
| HP-62 | M | The page run id is created by the page backend when a run is requested and identifies the run for its whole life, across every resume. The `run_id` that `run_suite` writes on each record changes on every call, so it is stored on the record as an attempt id only and never used to group, count or compare runs. For EV-1, a run's record for a case is the one from its latest attempt. A failed attempt that a resume replaced is kept, marked as superseded by the later attempt, and not edited, so EV-5 holds. Run Again is a new page run id, as EV-5 requires of a re-run. |

## 10. Comparing runs

| ID | P | Requirement |
|---|---|---|
| HP-52 | M | Two or more runs can be selected and compared in one table in the form `build_report` produces: one column per run, one row per summary metric, then per-class results and per-case pass or fail. |
| HP-53 | M | Runs can only be compared when their test set content hash matches. Otherwise the page refuses and says the test sets differ. |
| HP-54 | M | Before showing a comparison, the page lists every setting that differs between the runs other than the model (judge, strategy, depth, classes, code commit). R137 requires everything except the model to be held constant, and a hidden difference makes the comparison misleading. |
| HP-55 | S | The comparison can be exported as the markdown report `write_report` produces, for the final report and for R100. This meets EV-48. |

Run-over-run diff and question-level regression listing are EV-45 and EV-46 and are not restated.

## 11. When a run fails

| ID | P | Requirement |
|---|---|---|
| HP-56 | M | A run that cannot start (test set fails to load, provider key missing, unknown strategy, depth not above zero) is refused before any model call, with a message naming the cause. No run record is left in `running`. |
| HP-57 | M | A provider failure on one case after retries is recorded for that case and the run continues, as `run_suite` does today. The page shows the count live (HP-26). |
| HP-58 | M | An error `run_suite` does not catch (only `ServiceUnavailableError` and `RateLimitError` are caught) ends the run. The run is marked `failed`, keeps every saved case, shows the error with the case id it occurred on, and is resumable under HP-29. Examples are a database error during retrieval and an authentication error from the provider. |
| HP-59 | M | Every run that ends without completing shows, in this order: its status (HP-47); a cause category from a fixed list (provider rejected the key, rate limit or quota reached, provider unavailable, database or retrieval error, test set error, cancelled by a user, server stopped, unexpected error); the case id it stopped on, or "before the first case"; cases saved out of planned; and whether resume is offered. The technical error follows underneath, with any key or connection string removed. |
| HP-60 | M | A judge failure on a case keeps the answer and records the judge error. `judge_answer` records three kinds: judge unavailable after retries, "no JSON in judge output", and "invalid JSON in judge output". The run summary shows the count of cases with a judge error, split by kind, rather than averaging fewer cases silently. Resume does not retry these, because the case has no top-level error. |
| HP-61 | S | A run whose answers came from a different model than the one selected is flagged. The harness now goes through the proxy (section 2), so this can happen today and is not handled: fallbacks are on for evaluation runs and the answering model is not recorded per case. `[ASSUMED]` |

## 12. Conflicts with existing requirements

Eight conflicts or gaps, one per row.

| Conflict | Resolution |
|---|---|
| EV-3 requires the full text of every retrieved chunk. `run_case` stores a 400-character `content_preview`. | EV-3 wins. Adding the full text as a new field on the record is an additive change and does not alter scoring. |
| EV-2, EV-4, EV-6 and EV-32 ask for fields the harness does not produce: resolved income year, scorer version or prompt hash, prompt version, corpus snapshot id, and the stage an error occurred at. | EV wins. Each is new work, not something the page can derive. Income year needs a resolver, which temporal precision also needs. Prompt hash and prompt version can be taken from `SYSTEM_PROMPT_TEMPLATE` and `JUDGE_PROMPT` as additive fields. Corpus snapshot id needs a corpus versioning decision that does not exist yet. Until then the columns read not recorded (HP-45). |
| EV-42 says every gated metric shows pass or fail on the page. HP-35 shows correctness and faithfulness without a verdict, and the card asks for metrics with pass/fail gates. | HP-35 wins until judge validation, `[ASSUMED]` pending team agreement. The gates are 0.85 and 0.95 on a 0 to 1 scale and the judge scores 1 to 5; any mapping between them would be a number this document invents. EVALUATION.md section 5 also says an unvalidated judge is not fit to gate anything. The page shows these two as "No gate on this scale" and counts them under HP-37 as not measured against a gate. EV-42 applies in full once a mapping is agreed and E-4 reports judge agreement. |
| EV-5 requires immutable records. `write_report(rescore=True)` overwrites result files in place. | EV-5 wins for stored runs (HP-49). The console path is unchanged. |
| EV-30 and EV-31 keep `no_source` and `refused` apart. The harness refusal regex matches no-source wording ("could not find", "no relevant source", `REFUSAL_PATTERNS` in `harness.py`), so both set `refused`. | EV wins. The page cannot derive `no_source` from current fields. Until a scorer separates them, the outcome shows as `refused` with a note that it may be no-source. Open question 4. |
| EV-49 lets reviewer accounts reach `/testing`. No reviewer role exists, and `RequireTeam` admits only `team`. | Neither is changed here. HP-6 forbids giving reviewers `team`. Open question 2. |
| R137 asks for models behind the LiteLLM proxy "using its existing fallbacks". The harness now uses the proxy, and a fallback during an evaluation run would attribute one model's answers to another. | Attribution wins (HP-61). Whether evaluation goes through the proxy is open question 1. |
| `docs/ITERATION-AND-EXPLORATION.md` I-2 (a file that is not on `main`) put a 22-case run at roughly 10 to 15 minutes. The result files show 13 to 19 minutes (section 2.1). | The result files are the source. The difference does not change any requirement. |

The reuse rule, stated so it can be checked: the page may add optional parameters or fields to the harness (a per-case callback, a stop check, the full chunk text) but may not change how any metric is computed. The existing tests in `tests/evaluation/` pass unchanged, and the console script gives the same results file for the same inputs.

`docs/model_evaluation_report.md` contains figures that do not trace to any file in `benchmarks/results/` or `benchmarks/reports/`. The page does not import or display them.

## 13. Acceptance checks

Card R102 tests the page. Each of its checks maps to requirements here.

| R102 check | Pass when | HP |
|---|---|---|
| Run starts from the page and completes | A `team` user starts a full-set run (22 cases when written, 50 now), closes the tab, reopens it, and finds the run `completed` with every case saved | HP-7, HP-11, HP-20, HP-26 |
| Summary metrics shown against their gates | Every row of the section 7 table appears with value, gate and verdict or "Not measured", and the values equal `build_report` output for the same result file | HP-33 to HP-37 |
| Per-question results show sources, answer and scores | Each row expands to the content in HP-42 | HP-41, HP-42 |
| Failing questions are marked and the filter works | Filtering to failed cases lists exactly the cases `case_failures` flags | HP-44 |
| Interrupted or failed run shows a clear error | Cancelling mid-run, removing a provider key, and stopping the server each give a distinct status and a message with the cause category, the case id it stopped on, and cases saved out of planned (HP-59); saved cases are kept and resume works | HP-28, HP-29, HP-32, HP-56 to HP-59 |

Also to test, though not on the R102 list: a `staff` account and an unauthenticated call get 403 and 401 (HP-2, HP-3); two simultaneous starts produce one run (HP-24); and resume refuses changed settings (HP-30).

## 14. Open questions

| # | Question | Affects |
|---|---|---|
| 1 | Evaluation runs now go through the LiteLLM proxy with its fallbacks on. Should fallbacks be turned off for evaluation, or the answering model recorded per case? | HP-11, HP-12, HP-61 |
| 2 | How do validation reviewers sign in, given there is no reviewer role? This is the same gap AU-10 records. | HP-6, EV-22, EV-49 |
| 3 | What depth does the deployed assistant use? The chat retriever uses 5; the harness default is 6. | HP-17, HP-18 |
| 4 | How should `no_source` be told apart from `refused`? This likely belongs with the grounding and refusal rules in card R119. | HP-41, EV-30, EV-31 |
| 5 | Is one run at a time acceptable, or does the team need parallel runs on separate provider keys? | HP-22, HP-23 |
| 6 | Which judge model is the default? All existing runs used `groq/openai/gpt-oss-120b`, which is also a candidate. | HP-15, HP-16 |

## 15. Handoff to UX and Dev

| Card | Owner | Uses |
|---|---|---|
| R121 Harness page wireframe | Manan | Sections 3 to 8 and 10: settings panel, run and stop controls, queue and progress states, the section 7 metric table with "Not measured" rows, per-question rows, run history, and every failure status in HP-47 |
| R135 Run controls and summary build | Manan | HP-7 to HP-40, HP-56 to HP-60, using the functions in section 2.2 |
| R95 Per-question results build | Manan | HP-41 to HP-44, HP-50 |
| R102 Test the harness page | Shihong | Section 13 |
| R137 A/B setup via LiteLLM | Shihong | HP-11, HP-12, HP-61, open question 1 |
| R100 Model A/B run and report | Shihong | HP-14, HP-52 to HP-55 |
| R131 Expand benchmark to 30-50 questions | Ronith | A larger `questions.jsonl` changes its content hash, so runs before and after cannot be compared (HP-53) |
| R132 Model A/B scoring criteria | Ronith | Any A/B thresholds it sets are shown in the comparison view (HP-52); it does not change the section 7 gates |

The backend endpoints and background execution (item I-2 in `docs/ITERATION-AND-EXPLORATION.md`, which is not on `main`) are now built in `app/routes/testing.py`; run storage is not. Card numbers (R95, R102 and so on) are historical planning labels.

## 16. Traceability

| Source | Covered by |
|---|---|
| Card R116, existing evaluation script reused, not rewritten | Section 2.2, HP-33, section 12 reuse rule |
| Card R116, who can run the harness | HP-1 to HP-6 |
| Card R116, how a test set and model are selected | HP-7 to HP-19 |
| Card R116, metrics shown with their pass/fail gates | Section 7, HP-33 to HP-40 |
| Card R116 description, what each per-question result shows | HP-41 to HP-44 |
| Card R116 description, how runs are stored and compared | HP-45 to HP-55 |
| Card R116 description, what happens when a run fails | HP-28 to HP-32, HP-56 to HP-61 |
| TESTING-PAGE-REQUIREMENTS.md EV-39, interrupted run | HP-29, HP-32, HP-40 |
| TESTING-PAGE-REQUIREMENTS.md EV-42 to EV-44, gates on the page | HP-33 to HP-37 |
| TESTING-PAGE-REQUIREMENTS.md EV-49, access isolation | HP-1 to HP-6 |
| REQUIREMENTS.md NF-3 and NF-4, quality measured and re-measured | The page as a whole: a run anyone on the team can start and compare |
| ITERATION-AND-EXPLORATION.md I-2 | Sections 5, 6, 9 and 11 |

Only the items in the Status banner are built. The "Verified in" entries are readings of the code on `main`, not tests of a running page. Requirements not listed as built remain the target for the next team.
