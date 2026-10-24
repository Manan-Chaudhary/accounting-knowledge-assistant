# Testing and evaluation page requirements

Team 83, Alfa Focus Knowledge Assistant.
Drafted 2026-08-26 by Ronith Mugundakumar.
Surface: `/testing` (React page `frontend/src/pages/Testing.tsx`) and its API in `app/routes/testing.py`.

Defines what the evaluation review page must capture. Derived from the metrics in [`EVALUATION.md`](EVALUATION.md) section 4, the judge design in section 5, and the page sketch in section 6. Requirement IDs are `EV-n` and are stable, per the traceability rule in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10.

**Status: partially implemented (a run-and-summary page, not the review page described here).** Built and demoed: the `/testing` page, restricted to the `team` role on server and browser (EV-49 in part; there is no reviewer role), which starts, polls and stops an evaluation run of the 50-case benchmark against a chosen model (one model per run), and shows aggregate metrics with gate verdicts (EV-41 not built per class; EV-42, EV-44 in part; EV-39 in part, partial runs are labelled and gates marked informational). Not built: stored per-question records (EV-1 to EV-6; runs live in memory and temp files), per-question inspection, side-by-side model comparison (EV-24 to EV-29), human labelling and agreement (EV-21 to EV-23, EV-34 to EV-36), the `no_source`/`refused`/`error` outcome split (EV-30 to EV-33), diff, filter and export (EV-45 to EV-48), and the planned metrics, which the page lists as "Not implemented". See [`HARNESS-PAGE-REQUIREMENTS.md`](HARNESS-PAGE-REQUIREMENTS.md) section 2 for the detail. No accountant labelling was done; the client was never met. Requirements marked `[ASSUMED]` need confirmation before they drive a sprint. The reviewer workflow in section 6 assumes an Alfa Focus accountant is available to label, which is unconfirmed. Everything else is derivable from the evaluation design and does not wait on the client.

Priorities are MoSCoW: **M** must, **S** should, **C** could.

## 1. Purpose

`/testing` is the only screen a client ever touches during development, and the only place a metric number can be traced back to the answer that produced it. It has two jobs that pull in different directions:

1. Show whether the system passes its gates, aggregated, at a glance.
2. Let a person inspect one question deeply enough to say why a number is what it is.

A page that does only the first is a dashboard and cannot be used to fix anything. A page that does only the second cannot be used to decide whether to merge.

Out of scope: `/testing` is not reachable by firm staff and is not part of the assistant product. It is a development and validation surface. Per [`REQUIREMENTS.md`](REQUIREMENTS.md) section 2, its user is Team 83, plus an Alfa Focus accountant during judge validation.

## 2. Users

| User | Uses it to | Implication |
|---|---|---|
| Team 83 developer | Run the benchmark, see which gates fail, drill into a failure | Needs raw retrieval detail and scorer verdicts |
| Team 83, at review | Show per-class results and judge agreement | Needs aggregates and a run-over-run diff |
| Alfa Focus accountant | Label answers for judge validation | Needs a stripped labelling view with no scores visible. See EV-22 |

## 3. What one evaluation record holds

The `EvalResult` model in [`EVALUATION.md`](EVALUATION.md) section 6 needs two fields it does not currently name: `model_id`, because the page compares several LLMs on the same question, and `outcome`, because a question that returned no answer is not the same as a question that returned a wrong one.

| EV | P | Requirement |
|---|---|---|
| EV-1 | M | One record exists per combination of run, question and model. A run over 28 questions against 3 models produces 84 records, not 28 (the benchmark now has 50 questions). |
| EV-2 | M | Each record stores the run id, question id, question class, model id, the answer text as returned, the ordered list of retrieved chunk ids with their scores, the resolved income year used for the query, the outcome (see section 6), and a created timestamp. |
| EV-3 | M | Each record stores the full text of every retrieved chunk as it was at run time, not a reference resolved at read time. A chunk that is later re-indexed or superseded must not silently change what a past run appears to have retrieved. |
| EV-4 | M | Each record stores every scorer verdict as its own field, per section 4, with the scorer version or prompt hash that produced it. |
| EV-5 | M | Records are immutable once written. A re-run creates a new run id. Correcting a mistake is a new record, not an edit. |
| EV-6 | S | Each record stores the pipeline configuration in force: retriever settings, prompt version, and the corpus snapshot id. Without this a run is not reproducible and a diff is not attributable. |

EV-3 is the requirement most likely to be skipped and the one that quietly invalidates every past run when it is. Storing chunk ids alone is cheaper right up to the first corpus refresh.

## 4. A scoring field for every metric

Every metric defined in [`EVALUATION.md`](EVALUATION.md) section 4 has a corresponding per-question input below. Aggregate metrics are not stored directly; they are computed from the per-question inputs named here, so that any headline number can be traced to the rows that produced it.

**Source** is where the value comes from: `code` is deterministic and needs no LLM, `judge` is LLM-scored, `human` is reviewer-entered.

### 4.1 Retrieval metrics

| EV | P | Metric | Per-question input | Type | Source |
|---|---|---|---|---|---|
| EV-7 | M | Recall@10 | `expected_source_found_in_top_10` | boolean | code |
| EV-8 | M | Context precision | `relevant_chunk_positions`, the ranks of chunks judged relevant | list of int | judge |
| EV-9 | M | MRR | `first_relevant_rank`, null where no relevant chunk was retrieved | int or null | code |
| EV-10 | M | Temporal precision | `chunks_valid_for_year` over `chunks_retrieved`, both stored, not just the ratio | two ints | code |
| EV-11 | M | Corpus routing accuracy | `expected_corpus`, `retrieved_corpus_mix` | enum, counts | code |

EV-10 stores the numerator and denominator rather than the computed share. A temporal precision of 0.80 means something different over 5 chunks than over 50, and the gate is 0.98.

### 4.2 Generation metrics

| EV | P | Metric | Per-question input | Type | Source |
|---|---|---|---|---|---|
| EV-12 | M | Faithfulness / groundedness | `groundedness_score`, plus the per-claim decomposition the judge produced | float, list | judge |
| EV-13 | M | Answer relevancy | `relevancy_score` | float | judge |
| EV-14 | M | Correctness | `correctness_score`, and `correctness_applicable` false where the question has no golden answer | float or N/A | judge |
| EV-15 | M | Citation resolution | `citations_total`, `citations_resolved`, `unresolved_markers` listed individually | two ints, list | code |
| EV-16 | M | Citation support | `citation_support` scored per citation marker, not once per answer | list of float | judge |
| EV-17 | M | Corpus attribution | `attribution_correct` per labelled section | list of boolean | code |

EV-14 must distinguish not-applicable from zero. A question with no golden answer scoring 0.0 on correctness would drag an aggregate down for a reason that has nothing to do with the system.

EV-16 is scored per marker because an answer can be grounded overall while citation `[2]` points at the wrong paragraph. Storing one number per answer loses exactly the failure the metric exists to catch.

### 4.3 Behavioural metrics

| EV | P | Metric | Per-question input | Type | Source |
|---|---|---|---|---|---|
| EV-18 | M | Refusal recall and precision | `must_refuse` from the benchmark, `did_refuse` observed, `refusal_warranted` where a refusal was not required | boolean x3 | code, human for the third |
| EV-19 | M | Stale-premise correction | `premise_corrected`, applicable to C3 only, marked not-applicable elsewhere | boolean or N/A | judge |
| EV-20 | M | Income-year scoping | `volatile_claims_total`, `volatile_claims_with_year` | two ints | code |

EV-18 is the one place a single boolean cannot serve. Refusal recall and refusal precision are different questions asked of different denominators, and [`EVALUATION.md`](EVALUATION.md) section 4 requires they always be reported together. A system that refuses everything scores 1.00 on recall.

### 4.4 Human label

| EV | P | Requirement |
|---|---|---|
| EV-21 | M | Each record can carry one human label per reviewer, on the four-point scale from [`EVALUATION.md`](EVALUATION.md) section 5: correct, partially correct, wrong, dangerous. |
| EV-22 | M | The labelling view shows the question, the answer, and the retrieved sources only. It does not show any scorer verdict, any other reviewer's label, or which model produced the answer. A judge validated against contaminated labels reports an agreement figure that means nothing. |
| EV-23 | S | A reviewer can attach a free-text note to a label. The note is required when the label is `dangerous`, because that is the class the final report has to name examples from. |

## 5. Comparing models

The page compares several LLMs on the same question. This is what makes ties possible and what the model selection decision rests on.

| EV | P | Requirement |
|---|---|---|
| EV-24 | M | A single question view shows every model's answer side by side, each with its own scorer verdicts and its own retrieved chunks, since retrieval may differ per model. |
| EV-25 | M | Model identity is shown in the developer view and hidden in the reviewer labelling view, per EV-22. |
| EV-26 | S | A reviewer can record a preference between models for one question: model A, model B, or tie. |
| EV-27 | M | A tie is a recorded value, not an absent one. An unanswered preference and a declared tie are different states and must be stored differently, or the count of ties becomes the count of questions nobody got to. |
| EV-28 | S | Where a preference is recorded, the reviewer can select a reason from a fixed list: better sourcing, better scoping, more appropriate refusal, clearer structure, other with a note. |
| EV-29 | S | Aggregate model comparison reports wins, losses and ties per model, with ties shown as their own column and never split across the two models or dropped. |

EV-27 exists because ties are the expected outcome on a large share of C1 single-fact questions, where any competent model returns the same figure. If ties are not recordable the comparison silently over-reports differences.

## 6. Edge cases

The three named in the task, plus two that fall out of them.

| EV | P | Situation | Required recording |
|---|---|---|---|
| EV-30 | M | No answer returned because the system correctly found no supporting source | `outcome = no_source`. Scored against CH-6 and CH-10 behaviour, not counted as a wrong answer. Correctness is not-applicable. |
| EV-31 | M | No answer returned because the system correctly refused | `outcome = refused`. Feeds EV-18. Not a failure unless `must_refuse` is false. |
| EV-32 | M | No answer returned because the model or retriever errored or timed out | `outcome = error`, with the error and the stage it occurred at. Excluded from every quality metric denominator and reported separately as a run completeness figure. |
| EV-33 | M | An error is silently treated as a wrong answer | Must not be possible. EV-30, EV-31 and EV-32 are three distinct outcomes and the schema must not collapse them into one null answer field. |
| EV-34 | M | Two reviewers give different labels to the same answer | Both labels are stored. Neither overwrites the other. The record shows as disagreed rather than resolving to one value. |
| EV-35 | M | A disagreement needs resolving | A third adjudicated label can be added, marked as adjudication and attributed. The original two labels remain visible. An adjudicated value must never replace the source labels, because inter-rater agreement is computed from independent labels and adjudication would inflate it. |
| EV-36 | S | Agreement needs reporting | The page reports pairwise agreement and Cohen's kappa over questions labelled by two or more reviewers, with the sample size shown next to it. |
| EV-37 | M | Two models are judged equal on a question | `preference = tie`, per EV-27. |
| EV-38 | S | Two models tie on aggregate score for a class | The class is reported as tied. The page does not break the tie by ordering, since an arbitrary winner in a results table gets read as a real one. |
| EV-39 | S | A run is interrupted part way | The run is marked incomplete with the count of questions attempted against the count planned. Partial results are viewable but every aggregate on the page is labelled as partial. |
| EV-40 | S | A question has no golden answer | Correctness is not-applicable per EV-14 and the question is excluded from the correctness denominator, not scored zero. |

EV-33 is the requirement to write the test for first. The natural schema, one nullable answer field, makes all three no-answer cases indistinguishable, and an outage during a benchmark run then reads as a quality regression.

## 7. Aggregation, gates and diff

| EV | P | Requirement |
|---|---|---|
| EV-41 | M | Scores are aggregated per question class, not only across the whole set. An 85 percent average hides a 40 percent on multi-hop. |
| EV-42 | M | Every metric with a gate in [`EVALUATION.md`](EVALUATION.md) section 4 shows its gate alongside its value, with pass or fail resolved on the page rather than left to the reader. |
| EV-43 | M | Citation resolution renders as pass or fail against 1.00, not as a score. It is a hard gate with no partial credit. |
| EV-44 | M | Retrieval and generation metrics are shown as separate groups, so a failure can be attributed to the stage that caused it. |
| EV-45 | S | A run can be diffed against a previous run, showing per-class and per-metric movement, with regressions distinguished from improvements. |
| EV-46 | S | The diff can be opened down to the question level, listing questions whose outcome changed between the two runs. |
| EV-47 | S | A run can be filtered to one class, one outcome, or one model. |
| EV-48 | C | A run and its results can be exported for inclusion in the final report. |

## 8. Access and data handling

| EV | P | Requirement |
|---|---|---|
| EV-49 | M | `/testing` is reachable only by authenticated Team 83 accounts and the reviewer accounts created for judge validation. It is not linked from the assistant interface. |
| EV-50 | M | Benchmark questions contain no client data, per [`REQUIREMENTS.md`](REQUIREMENTS.md) DH-2. If a production trace is promoted into the benchmark, it must be checked for identifiers before it is stored. |
| EV-51 | S | Reviewer identity is stored against labels, since kappa requires knowing who labelled what. It is not shown in any aggregate view. |

## 9. Open questions

Each blocks or reshapes something above. To go to the client meeting alongside the questions in [`CLIENT-MEETING-QUESTIONS.md`](CLIENT-MEETING-QUESTIONS.md).

| # | Question | Affects |
|---|---|---|
| 1 | Will an Alfa Focus accountant be available to label 40 to 60 responses, and roughly when? | The whole of section 6. Without two labellers there is no disagreement to record and no kappa to report. |
| 2 | Can two people label independently, or only one? | EV-34 to EV-36. With one labeller, agreement cannot be computed and the judge cannot be validated as designed. |
| 3 | Is the four-point scale meaningful to an accountant, in particular the wrong versus dangerous distinction? | EV-21. The distinction is the one that matters most in the final report and it has not been tested on a domain expert. |
| 4 | How many models are actually in scope for comparison? | Section 5. Sizing the side-by-side view for two models is a different layout problem to sizing it for four. |

`[ASSUMED]` Questions 1 and 2 are currently assumed to be yes. If either is no, EV-34 to EV-36 become unbuildable as written and the judge validation step in [`EVALUATION.md`](EVALUATION.md) section 5 needs redesigning rather than dropping.

## 10. Traceability

| Source | Covered by |
|---|---|
| EVALUATION.md section 4, retrieval metrics | EV-7 to EV-11 |
| EVALUATION.md section 4, generation metrics | EV-12 to EV-17 |
| EVALUATION.md section 4, behavioural metrics | EV-18 to EV-20 |
| EVALUATION.md section 5, judge validation | EV-21 to EV-23, EV-34 to EV-36 |
| EVALUATION.md section 6, page behaviour | EV-41 to EV-48 |
| Task brief, edge cases | EV-30 to EV-40 |
| Task brief, model answer per LLM | EV-1, EV-24 to EV-29 |

Every metric named in [`EVALUATION.md`](EVALUATION.md) section 4 has an input above. Only the items in the Status banner are built; the rest are requirements for the next team, and the difference should stay visible. Nothing here has been validated with the client.
