# Handover Document: Business Analyst sections

Team 83, Alfa Focus Knowledge Assistant.
Written 2026-10-22 by Ronith Mugundakumar (BA), from the repository on `main` (commit `c059f82`), the Planner export of 2026-10-22 and the documents in this folder.

**How to use this file.** Each heading carries its number from the course template (COSC 2048 Handover document). Paste the text under it into the Word template, and delete this note and the closing "Open points for the compiler" section. Section 4.4 and 4.5 are not in the template: the template has no place for the document library or the evaluation results, which a continuing team needs, so they sit under Requirements. Move them if the compiler prefers. Where the text says "we assume", the client never confirmed it, because the client was never met.

A Word version with the same content, in the course template's styles, is `docs/HANDOVER-BA-SECTIONS.docx` (generated from this file on 2026-10-22). After that date, edit the Word file for the submission and keep this file as the record.

---

## 2. Project Overview

### 2.1 Problem Statement

**Owner: Business/QA, Ronith Mugundakumar**

Alfa Focus is a tax and accounting firm in South Melbourne. SMSF (self-managed super fund) administration is one of its main service lines, and many of its customers are other professionals, such as accountants and financial planners, who outsource the administration of their own clients' funds.

Its staff answer the same technical questions again and again: what a cap or threshold is this year, what it was in a past year, and which rules apply to a fund's situation. Three things make this costly:

- **The rules change often.** 1 July 2026 alone brought a new tax on large balances (Division 296), payday super and an indexed transfer balance cap. A figure that was right last year is wrong this year.
- **Accountants lose time re-deriving answers.** The source is in ATO pages, legislation and professional standards that are long and spread across many sites.
- **Two staff can give a referring planner two different answers.** For a firm that lives on referrals, consistency matters more than speed.

What the firm needs from a tool is an answer with its source shown, which declines instead of guessing, and which never replaces the judgement of the registered tax agent who is professionally liable for the advice. We assume the firm's own procedures are held by senior staff and are not written down. That is unconfirmed, and it decides whether the firm-procedure part of the product can exist.

The client was never met. This statement comes from public research, with confidence markers, in `docs/CLIENT-BRIEF.md`, and from the team's own reasoning in `docs/DOMAIN-PRIMER.md`. The 14 questions to put to Alfa Focus first are in `docs/CLIENT-MEETING-QUESTIONS.md`.

### 2.2 Goals & Success Metrics

**Owner: Business/QA, Ronith Mugundakumar**

The goals follow the design principles in the README. Each was set with a measure so that quality is tested, not asserted (requirement NF-3). The measures and gates are defined in `docs/EVALUATION.md`, and how they were applied is in section 4.5.

| Goal | Measure and target | Result at handover | Met? |
|---|---|---|---|
| Every answer carries a source the reader can check | Citation resolution: every citation number points at a passage the model was given. Target 100% | None of the three models compared met it: each wrote at least one citation number with no matching passage. The chat shows such a number as an unmatched chip. Citations show the document name on hover but cannot be opened | No |
| The assistant declines instead of guessing | Refusal recall 95% or more and refusal precision 85% or more on the benchmark | One of three models met both on the 21 cases scored (1.00 and 1.00). The other two missed precision (0.83 and 0.80) | Partially |
| Retrieval finds the right document | Source hit (recall) 95% or more | 100% source hit on the 22 cases run, and a mean reciprocal rank of 0.96. Keyword-only search found the source in 41% | Yes, on 22 of 50 cases |
| Answers arrive fast enough to use | 95 in 100 answers within 8 seconds | 176.8 seconds at the 95th percentile in a five-question test on 2026-10-14, almost all of it waiting for the first word from free-plan models | No |
| Year-dependent figures state their income year | 95% or more of such claims carry the year | Not measured. No scorer was built. The system prompt requires it | Not measured |
| Staff can add documents without a developer | A user can upload a file and see it become searchable | Done through the Documents page. Document type, effective date and accounts still need a developer | Partially |
| An accountant can use it after a short walkthrough | User acceptance session | The test script was written (section A.3) and never run | Not tested |
| Quality is measured, not asserted | A benchmark set and a repeatable harness | 50-case benchmark, harness, report script and an evaluation page | Yes |

The client's stronger business case, consistency across staff, was not measured. It needs repeated runs of the same questions, which the final model comparison is designed to give (section 4.5).

### 2.3 Scope & Out of Scope

**Owner: Project Manager + Business/QA. Business/QA draft below; the PM confirms.**

Delivered:

- Sign-in with three roles (`staff`, `admin`, `team`) and a signed session.
- A chat page with streamed answers, retrieval from the document library, numbered citations, a model selector and saved chat history with delete.
- A Documents page: upload (PDF, DOCX, TXT), ingestion through n8n, statuses, retry, search by name and delete for `admin` and `staff`.
- Hybrid retrieval (vector and keyword search fused by reciprocal rank fusion, then reranked) and a gate that declines personal-advice questions and questions with no retrieved passage.
- A library of 73 official documents built and available to load (section 4.4).
- A 50-question benchmark, an evaluation harness, a comparison report, and an evaluation page for the project team.
- Written requirements, test scripts, user and admin guides, and this handover.

Out of scope or not delivered:

- Answers from the firm's own procedures. No firm documents exist, so there is no second library. *Blocked: client never met.*
- Opening a cited passage in a viewer, copying an answer with its sources, renaming a chat, and feedback buttons. *Not built in the time available.*
- Document type, effective date and version fields, and filtering by them. *Designed (UP-2, UP-5), not built.*
- Reading scanned PDFs (OCR) and a dashboard of unanswered questions. *Not built.*
- Security hardening: prompt-injection testing, automatic detection of client identifiers, a threat model. *Descoped.*
- A hosted, supported production service with continuous deployment. *Not delivered: see section 9.2.*
- By design, never in scope: an interface for the firm's clients or fund trustees, calculating a member's personal position, producing a document without a registered agent reviewing it, and writing to the firm's practice-management software (`docs/REQUIREMENTS.md` section 1).

---

## 4. Requirements

### 4.2 User Stories

**Owner: UX/Research + Business/QA. Business/QA draft; UX confirms the statuses of the screen stories.**

Statuses are what the code on `main` does on 2026-10-22, not what was planned. Where a story is delivered with a caveat, the caveat is in the table after this one. The IDs are provisional: reconcile them with the story list in the master document.

| ID | User story | Priority | Status |
|---|---|---|---|
| US-01 | As a staff member, I want to sign in with my email and password so that only authorised people use the assistant. | Must | Delivered |
| US-02 | As an administrator, I want roles so that only permitted users delete documents or see the evaluation page. | Must | Delivered |
| US-03 | As an administrator, I want to create and disable accounts so that I control who has access. | Should | Delivered |
| US-04 | As an accountant, I want to ask a question in plain language and get an answer drawn from approved documents so that I find the rule quickly. | Must | Delivered |
| US-05 | As an accountant, I want numbered citations in the answer that name the source document so that I can see where a statement came from. | Must | Delivered |
| US-06 | As an accountant, I want to click a citation and see the cited passage, highlighted, with a link to the original so that I can verify the answer. | Must | Not delivered |
| US-07 | As an accountant, I want the answer to appear as it is written, and to stop it, so that I am not left waiting for a blank screen. | Should | Delivered |
| US-08 | As an accountant, I want the assistant to say plainly when no source covers my question so that I am not given a guess. | Must | Delivered |
| US-09 | As an accountant, I want the assistant to decline personal advice and member-specific figures so that the firm never gives them from a tool. | Must | Delivered |
| US-10 | As an accountant, I want year-dependent figures to name their income year so that I do not use the wrong year's cap. | Must | Delivered |
| US-11 | As an accountant, I want a reminder not to type client identifiers so that I do not put client data into the tool. | Must | Delivered |
| US-12 | As an accountant, I want my chats saved and listed so that I can return to an earlier question. | Should | Delivered |
| US-13 | As an accountant, I want the assistant to use my earlier messages when I ask a follow-up so that I do not repeat myself. | Should | Not delivered |
| US-14 | As an accountant, I want to delete a chat so that I can remove one I no longer need. | Should | Delivered |
| US-15 | As an accountant, I want to rename a chat so that I can find it again. | Should | Not delivered |
| US-16 | As an accountant, I want to copy an answer with its sources so that I can paste it into an email. | Could | Not delivered |
| US-17 | As an accountant, I want to choose which AI model answers so that I can try another when one is slow or unavailable. | Could | Delivered |
| US-18 | As an administrator, I want to upload a document and have it become searchable without a developer so that I can keep the library current. | Must | Delivered |
| US-19 | As an administrator, I want to see whether each document is pending, processing, ready or failed so that I know when it can be used. | Must | Delivered |
| US-20 | As an administrator, I want to retry a failed document so that a temporary fault does not need a developer. | Should | Delivered |
| US-21 | As an administrator, I want to see why a document failed so that I can fix the cause. | Should | Not delivered |
| US-22 | As an administrator, I want to delete a document so that withdrawn material leaves the library. | Should | Delivered |
| US-23 | As an administrator, I want to search the document list by name so that I can find a file. | Should | Delivered |
| US-24 | As an administrator, I want to filter the document list by status, type and date so that I can review the library. | Should | Not delivered |
| US-25 | As an administrator, I want to record whether a document is law, guidance or firm procedure, and the date it applies from, so that the assistant can use the right one for the right year. | Must | Not delivered |
| US-26 | As an administrator, I want a newer version of a document to supersede the old one while keeping it for past years so that past-year questions still work. | Should | Not delivered |
| US-27 | As an accountant, I want answers that include how Alfa Focus handles a matter so that I follow firm practice. | Should | Not delivered |
| US-28 | As a project team member, I want to run the benchmark against a chosen model from a page so that I can check quality after a change. | Must | Delivered |
| US-29 | As a project team member, I want to see each question's result, its retrieved sources and its scores so that I can find where the assistant fails. | Should | Not delivered |
| US-30 | As a project team member, I want a side-by-side report of several models so that I can choose one. | Should | Delivered |
| US-31 | As a new developer, I want to run the whole system from the repository with Docker Compose so that I can take over the project. | Must | Delivered |
| US-32 | As the firm, I want the assistant hosted and supported for daily use so that staff can rely on it. | Should | Not delivered |

**Caveats on delivered stories.**

| Story | Caveat |
|---|---|
| US-01, US-02 | Any signed-in user can upload and retry documents, and the record stores the uploader as the word "user". Only the delete action is limited by role. |
| US-03 | By command line only (`scripts/create_app_user.py`). There is no page for accounts. |
| US-05 | The document name appears on hover. A reopened chat shows the numbers without names. The harness found invalid citation numbers in every model tested. |
| US-08, US-09, US-10 | Enforced by the system prompt and by a phrase-based gate. They are measured on the benchmark only in part (section 4.5), and the income-year behaviour is not measured. The personal-advice gate returns a fixed message and does not set out the rules. |
| US-12, US-14 | The list shows the 20 most recent chats. Deleting a chat does not check that the chat belongs to the signed-in user before removing its messages (section 9.4). |
| US-18 | Large documents take many minutes, the page does not refresh its own status, and the free embedding quota can run out. |
| US-31 | The steps in the README have not been followed by a person outside the team. |

### 4.3 Non-Functional Requirements

**Owner: Developers + Business/QA**

| Category | Requirement | Met? |
|---|---|---|
| Performance | 95 in 100 answers complete within 8 seconds (NF-1, `docs/EVALUATION.md`) | No. 176.8 s measured on 2026-10-14 (five questions, free-plan models, reranker not yet included) |
| Quality measurement | Answer quality is measured against a benchmark (NF-3) | Yes. 50 cases, harness and report |
| Quality control | Changes to prompts, retrieval or sources are re-measured before merge (NF-4) | No. Continuous integration compiles the code only; the test and benchmark steps are not run |
| Usability | An accountant can use it after a short walkthrough (NF-2) | Not tested. The user acceptance session was not run |
| Security: access | Only signed-in firm users reach any page (DH-5) | Partially. Pages and APIs need a session. The older `/chat` route is open if `CHAINLIT_AUTH_SECRET` is not set, and the app refuses to start in production without it |
| Security: secrets | Credentials stay in environment configuration and are never committed (DH-9) | Yes, with one incident. A database connection string was committed and removed on 2026-10-04 (pull request 72). It will still be in earlier commits, so rotate it if that has not been done |
| Privacy | No client data goes to a service without contract terms that prohibit training on it (DH-1) | No. Generation uses free plans whose terms were not confirmed. The Gemini free tier is flagged in `docs/LLM-BACKEND-CANDIDATES.md` |
| Privacy | Users are told not to enter client identifiers (DH-3) | Yes. A notice sits under the question box |
| Retention | A retention period for questions and answers is agreed with the client (DH-8) | No. Chats are kept until the user deletes them. The client never set a period |
| Maintainability | The firm can add and correct sources without the development team (NF-5) | Partially. Upload and delete work. Document type and date fields, and accounts, need a developer |
| Handover | Documentation lets a firm with no IT staff run it (NF-6) | Partially. README, guides and this document exist. Nobody outside the team has followed them |
| Availability | A failure shows a plain message and never an unsourced answer (EC-12) | Partially. The chat shows an error message. The non-streaming fallback route skips the grounding gate |
| Cost | Running costs are visible (NF-7) | No. The harness does not record token use or price |
| Accessibility, browsers | No target was set | Not specified, not tested |

### 4.4 Document library

**Owner: Business/QA, Ronith Mugundakumar**

The assistant answers only from documents loaded into it. The library built for this project ("Corpus A", authority) holds 73 official documents in 75 files, all retrieved on 2026-09-25 from public sources. There is no firm-procedure library ("Corpus B").

| Publisher | Documents |
|---|---|
| Australian Taxation Office | 58 |
| Federal Register of Legislation | 5 |
| Accounting Professional and Ethical Standards Board | 4 |
| Tax Practitioners Board | 3 |
| Australian Accounting Standards Board | 2 |
| Australian Securities and Investments Commission | 1 |

By authority: 18 documents are law and ATO rulings, 53 are regulator guidance and professional standards, and 2 are accounting standards. They cover the seven SMSF use cases (compliance, property and borrowing, contribution caps, pensions and the transfer balance cap, residency, Division 296, and establishment and annual compliance) and wider topics such as Division 7A, fringe benefits tax, GST, payroll and super, and professional obligations.

**Where things are.** The files are in `corpus/`, one folder per topic. `corpus/sources.json` lists where each came from, and `corpus/manifest.json` records the source address, type, authority tier and chunk count. `docs/DOCUMENT-CORPUS.md` section 7 lists all of them.

**Load status.** The load into the database is not fully verified. An audit part-way through counted 42 documents and 2,293 passages (`docs/corpus_check_report.md`), and `docs/load_log.csv` records 35 files. Before relying on the library, count the ready documents:

```sql
select status, count(*) from documents group by status;
select count(*) from document_chunks;
```

The model comparison results in section 4.5 were produced before the full library was loaded.

**To add a document**

1. Add an entry to `corpus/sources.json` (or place a file in the right topic folder).
2. Run `python scripts/build_corpus.py --only <id>`, then `python scripts/validate_corpus.py`. The second script checks the file can be read and counts its chunks.
3. Upload the file on the Documents page, or run `python scripts/upload_corpus.py` for a batch (it skips files already ready). Reload the page until the status is `ready`.
4. Add a benchmark question that the new document answers, and run the benchmark (section 4.5).

**To update a document.** Give a year-specific document a new name for the new year and upload it as a new document, so that questions about past years still work. For a corrected copy of the same document, upload the new file, wait until it is ready, then delete the old one. There is no version control in the application.

**Limits.** The document list was assumed from public research and never confirmed by the client. The files are saved as published. Legislation and standards are the compilation current on the retrieval date: APES 110 is the June 2023 compilation, and later amendments are not included.

### 4.5 Evaluation approach and results

**Owner: Business/QA, Ronith Mugundakumar**

**Benchmark.** `benchmarks/questions.jsonl` holds 50 questions, each with the source document it should find, the expected behaviour, and, for 36 of them, a reference answer. Twenty are lookups of the kind accountants ask every day (12 single facts and 8 exact references), and the rest test the failure modes that matter in this domain: figures for a past year, a question built on an out-of-date figure, a member-specific figure the tool must not give, a request for personal advice, a ruling number that does not exist, and a question outside the subject. 14 are marked must-refuse. The reference answers were written from the library by non-experts. The questions are the team's estimate of real use, because the client's real questions were never obtained.

**What is measured.** The harness (`app/evaluation/harness.py`) runs each question through retrieval and generation and scores:

- **Retrieval:** whether the expected source was retrieved, and its rank.
- **Citations:** whether every citation number points at a passage the model was given. This is a code check, not a judgement.
- **Refusals:** whether the assistant declined when it should (recall) and only then (precision). The check is a pattern match over the wording.
- **Quality:** an AI judge scores correctness and faithfulness from 1 to 5. The judge has not been checked against human marking, so the scores guide and do not gate.
- **Time:** wall-clock time per question.

The gates are in `docs/EVALUATION.md` section 4. Citation support, income-year scoping, temporal precision and cost are defined but not measured. The same checks run from the command line (`scripts/run_evaluation.py`, `scripts/evaluation_report.py`) and from the evaluation page, which is for `team` accounts and shows totals but not individual questions.

**Results to date.**

| Test | When | Result |
|---|---|---|
| Retrieval, 22 questions, vector search only | 2026-10-04 | Right source found for 100% |
| Retrieval, 22 questions, keyword search only | 2026-10-06 | Right source found for 41% |
| Three-model comparison, 22 questions (`benchmarks/reports/comparison_2026-10-01.md`) | 2026-10-01 | Retrieval identical, 100% source hit; the models differ in citation numbering, refusals and tail latency |
| Same runs scored under the agreed A/B rules (`benchmarks/reports/ab_interim_2026-10-22.md`, `docs/MODEL-AB-RESULTS.md`) | 2026-10-22 | No model passes every gate. All three wrote a citation number with no matching passage. Two stated an unsourced dollar figure while declining. Provisional order: `qwen3.8-27b`, `gpt-oss-120b`, `gpt-oss-20b` |
| Latency, five questions | 2026-10-14 | 176.8 s at the 95th percentile against a target of 8 s |

**Model comparison result.** No model can be recommended to the client on this evidence. The three Groq models are the only ones compared, on 21 of the 50 questions, with one run each, a judge that was itself one of the candidates, and no cost or latency data. The model the application uses by default, Gemini 3.8 Flash, was never compared like for like. The comparison needs the full 50-question run on every candidate. `docs/MODEL-AB-SCORING.md` sets the rules for that run, and `scripts/ab_analysis.py` produces every number from the saved result files (command in `docs/MODEL-AB-RESULTS.md` section 8).

**Known limits of the evidence.** The benchmark is small, so one question moves a rate by 2 to 5 points. It is weighted to CGT and fringe benefits tax, because the first 22 questions were written for the four documents loaded at the time. Citation checks show that a passage was given to the model, not that it supports the claim. All saved model results cover 22 questions or fewer.

**To re-run.** Start the system, then run the benchmark from the evaluation page, or from the command line with a model name from `litellm/config.yaml`:

```bash
python -m scripts.run_evaluation --model gemini-3-8-flash --output benchmarks/results/<name>.jsonl --report benchmarks/reports/<name>.md
```

---

## 9. Handover Guide: Business Analyst contributions

### 9.4 Known Issues & Technical Debt (Business/QA contribution)

**Owner of section 9.4: Developers. The issues below were found while writing the requirements and test sections; the compiler merges them into the developers' table.** "Read" means found by reading the code and not reproduced in a running system.

| Issue | Severity | Suggested fix |
|---|---|---|
| Follow-up questions have no memory. The streaming chat route sends only the latest message to retrieval and to the model (`app/routes/chat_history.py`). The older route that kept history is not the one the chat page calls. Read | High | Pass the earlier turns to the stream, and rewrite the question for retrieval |
| No model tested passes the citation-resolution gate. Every model wrote citation numbers with no matching passage | High | Run the final comparison; add a citation check to the streaming path before the text is shown |
| Answers are slow: 176.8 s at the 95th percentile against 8 s | High | Move off free plans, then re-measure with `scripts/measure_latency.py` |
| Documents carry no type or effective date, so the assistant cannot choose the document that applied in a given year, which is the main failure mode of this domain | High | Add `corpus`, `effective_from` and `effective_to` columns and upload fields (UP-2); filter retrieval by income year |
| The "no source" gate only fires when retrieval returns nothing. Retrieval always returns the top passages, so a question outside the library still reaches the model, which must refuse unaided. Read | Medium | Add a minimum similarity score to the gate |
| The personal-advice gate matches phrases such as "should I" and "should my client". The message it returns does not set out the rules, as the requirement asks. "Should this client…" is not matched. Read | Medium | Widen the patterns; return the rules that bear on the question with citations |
| Deleting a chat removes its messages before checking the chat belongs to the user, and the streaming route accepts a thread id without checking its owner. A signed-in user who knows a thread's id can delete or add to it. Ids are random, so the risk is low. Read | Medium | Add the owner condition to both queries |
| Any signed-in user can upload and retry documents, and uploads record the uploader as "user" | Medium | Restrict upload by role and store the user's email |
| A database connection string was committed and removed on 2026-10-04 (pull request 72) and remains in the git history | Medium | Confirm the credential was rotated; rotate it if not |
| A hosted demo on Render was reported deployed on 2026-10-03 (Planner card "Deploy chainlit application"), while the README of 2026-10-22 says there is no hosting | Medium | Confirm whether the Render services are live, and shut them down or document them in 9.2 and 9.3 |
| The judge is not validated against human marking, and the A/B accuracy scores are partly self-judged | Medium | Have an accountant label 40 to 60 answers and report agreement (`docs/EVALUATION.md` section 5) |
| The library load is not fully verified (42 documents counted part-way, 35 files in the log) | Medium | Run the two queries in section 4.4 and record the result |
| Generation uses free plans with strict limits, and their no-training terms are unconfirmed (DH-1) | Medium | Choose a paid plan with confirmed terms before any real client use |
| The Documents page does not refresh its own status and does not show why a document failed | Low | Poll the status, show `failure_reason` |
| Continuous integration does not run the tests. Six tests in `tests/evaluation/test_harness.py` fail because they patch a function the harness no longer has | Low | Fix the tests, then enable the test step |
| The README's evaluation example names a provider path, but the harness calls the LiteLLM proxy, which knows only the aliases in `litellm/config.yaml` (use `gemini-3-8-flash`). Read | Low | Correct the example |

### 9.5 Recommended Next Steps (Business/QA contribution)

1. **Meet the client.** Put the 14 questions in `docs/CLIENT-MEETING-QUESTIONS.md` to Alfa Focus first. Most requirements are assumptions the client never confirmed, and the answer on firm procedures decides whether a second library is project work.
2. **Run the full model comparison** on every candidate, including the Gemini default, using the rules in `docs/MODEL-AB-SCORING.md`. Nothing about the model should be told to the client until this is done.
3. **Fix the citation check and conversation memory.** These are the two defects an accountant will meet first.
4. **Add document type and effective date,** then filter retrieval by income year. This is the main accuracy risk in the domain.
5. **Update the user acceptance script and run it** with an Alfa Focus accountant (section A.3).
6. **Validate the judge** against an accountant's labels.
7. **Settle data handling:** the plan and terms for generation, a retention period, and automatic checks for client identifiers.
8. **Make quality part of every change:** enable the tests in continuous integration and run the benchmark before merging a prompt or retrieval change.

---

## Appendix A: Test Plan & Scenarios

**Owner: Business/QA, Ronith Mugundakumar**

### A.1 Test Approach

Four kinds of testing were used:

- **Automated tests** (`pytest`): database, embedding, chunking, retrieval, reranker, grounding and evaluation scoring. The database tests need live credentials.
- **The benchmark:** 50 questions scored by the harness (section 4.5). It tests answer behaviour, not screens.
- **Task-level tests by a second team member.** The team rule is that the person who builds a feature does not test it. Each test card recorded its outcome in the Planner handoff notes, which are cited below. These are self-reported by the tester and were not independently reviewed.
- **User acceptance testing:** a script of eight scenarios was written for an accountant. It was not run.

Not covered: load and concurrent users, security testing, accessibility, other browsers and phones, and anything on a deployed environment other than the Render demo of 2026-10-03.

### A.2 Test Scenarios

TS-01 to TS-14 are the results the testers recorded in their Planner handoff notes, with the card's completion date. TS-15 to TS-20 come from the benchmark and the test run of 2026-10-22.

| ID | Scenario | Linked user story | Result |
|---|---|---|---|
| TS-01 | Sign-in page loads, and no other page opens without signing in | US-01 | Pass (login test, 2026-09-20) |
| TS-02 | Signing in works, signing out returns to the sign-in page, and upload needs no second sign-in | US-01, US-02 | Pass (authentication test, 2026-09-24) |
| TS-03 | Database connects and the schema matches (`tests/db`) | US-31 | Pass (2026-08-29) |
| TS-04 | The embedding service returns a vector of the right size (`tests/db/test_hf_embedding.py`) | US-18 | Pass, 1 test (2026-09-10) |
| TS-05 | Upload a file; it is stored and a record is created | US-18 | Pass (upload test, 2026-09-10) |
| TS-06 | A document goes through n8n, is chunked, embedded and stored, and can be imported and run with Docker Compose | US-18, US-19, US-31 | Pass (ingestion test, 2026-09-20) |
| TS-07 | The baseline pipeline retrieves the right source and cites it for four benchmark questions | US-04, US-05 | Pass, 4 of 4 (2026-09-27) |
| TS-08 | Switching the AI model does not disrupt the chat, prompt or retrieval | US-17 | Pass (2026-09-27) |
| TS-09 | The chat history list shows each account's own chats | US-12 | Pass (2026-09-27) |
| TS-10 | End-to-end on the Render demo: sign in, chat, retrieval with source, upload, n8n processing, and retrieval of the new document | US-01, US-04, US-05, US-18 | Pass (2026-10-03). Defects recorded: Markdown rendering, a `/documents` route clash, unclear errors, stale `pending` records |
| TS-11 | Chunking keeps headings, numbered clauses and tables together, and each chunk has an embedding | US-18 | Pass (2026-10-08) |
| TS-12 | The streaming route streams answers to the criteria on its card, and the non-streaming chat is unaffected | US-07 | Pass (2026-10-11) |
| TS-13 | Hybrid retrieval and the reranker return the expected sources | US-04 | Pass (2026-10-16) |
| TS-14 | Deleting a document removes the stored file and the chunks, excludes it from retrieval, cancels cleanly, and is refused for users without permission | US-22, US-02 | Pass, 5 of 5 checks (2026-10-18) |
| TS-15 | A made-up ruling number is not confirmed (benchmark EVAL-020, EVAL-021) | US-08 | Pass for all three models compared; one needed a manual read (2026-10-22) |
| TS-16 | A member-specific figure is declined without stating an amount (EVAL-017) | US-09 | Fail for two of three models, which stated an unsourced figure (2026-10-22) |
| TS-17 | A request for personal advice is declined (EVAL-018) | US-09 | Pass for one of three models; two declined for the wrong reason (2026-10-22) |
| TS-18 | A future-year figure is not invented (EVAL-019) | US-08 | Pass for all three models (2026-10-22) |
| TS-19 | Every citation number points at a passage the model was given | US-05 | Fail for all three models (2026-10-22) |
| TS-20 | Automated suite, evaluation and retrieval tests, run 2026-10-22 | US-28, US-30 | 50 passed, 6 failed. The six failures are in `test_harness.py` and predate this work (section 9.4) |

### A.3 User acceptance testing

**Outcome: not run.** No accountant or stand-in has used the assistant under a script, and the Planner export of 2026-10-22 has a card to write the script but none to run it. The script is `docs/UAT-SCRIPT.md`: eight scenarios (a cited answer, opening a citation, a follow-up, a question needing the income year, a question the library cannot answer, a request for personal advice, copying an answer, and renaming and deleting a chat), with feedback questions on trust and usefulness.

Before it is run, update the script to the application as built (checked against the code on 2026-10-22):

| Scenario | Expected in the script | What the application does |
|---|---|---|
| S1 | Sources listed under the answer | The chat page lists none. Citation numbers show the document name on hover |
| S2 | Click a citation to open a viewer | Not built |
| S3 | A follow-up is understood without repeating the subject | The assistant does not read earlier messages |
| S6 | The assistant declines, then sets out the rules with citations | The gate returns a fixed message with no rules or sources |
| S7 | A copy button | Not built |
| S8 | Rename a chat | Not built. Delete works with a browser confirmation box |

Mark S2, S3, S7 and the rename half of S8 "Not run: feature not in build", as the script allows. Run it with a stand-in participant who did not build the feature under test, and record the stand-in as a stand-in.

---

## Appendix B: Glossary (Business/QA contribution)

| Term | Definition |
|---|---|
| ATO | Australian Taxation Office |
| APES, APESB | Accounting Professional and Ethical Standards Board and its standards, such as APES 110 |
| Benchmark | The 50 questions in `benchmarks/questions.jsonl` used to score the assistant |
| BGE-M3 | The embedding model that turns text into numbers for searching |
| Chunk, passage | A piece of a document, about 1,200 characters, that is stored and searched on its own |
| Citation chip | The small grey numbered marker in an answer (for example the number 2 in square brackets), with the source name on hover |
| Corpus A, Corpus B | The library of official documents (A) and the firm's own procedures (B). Only A exists |
| Division 296 | A tax on large super balances that starts on 1 July 2026 |
| Embedding | A list of numbers that represents the meaning of a passage, so that similar passages can be found |
| Gate | A pass-or-fail threshold on a metric, or a check that stops an answer being given |
| Income year | The 12-month period for which a rate or cap applies, such as 2026-27 |
| Judge | An AI model that scores another model's answer. Its scores are guides until checked against human marking |
| LiteLLM | The proxy through which the application reaches Gemini, Groq and OpenRouter, and switches between them |
| LRBA | Limited recourse borrowing arrangement: a loan an SMSF uses to buy an asset |
| MRR | Mean reciprocal rank: how high the right source ranked, from 1 (first) down |
| n8n | The automation tool that starts document processing after an upload |
| pgvector | The database feature that stores embeddings and finds similar ones |
| RAG | Retrieval-augmented generation: finding passages first, then asking the model to answer from them |
| Reranker | A second model that reorders the retrieved passages by relevance |
| RRF | Reciprocal rank fusion: a way to merge the vector-search and keyword-search rankings |
| SMSF | Self-managed super fund |
| Transfer balance cap | The limit on how much can move into the tax-free retirement phase of super |
| TPB | Tax Practitioners Board |

---

## Open points for the compiler (not part of the handover)

- The story IDs and the story list are the BA's draft from the requirements and the code. Reconcile with the master document before submission, and have UX confirm US-06 and US-29.
- Deployment: the Planner (card "Deploy chainlit application", 2026-10-03) reports a Render deployment, and the README (2026-10-22) says there is no hosting. Section 9.2 and 9.3 must say which is true. If the Render services still run, list them and their accounts in 9.3.
- The final model comparison is outstanding. Replace the model comparison paragraph in section 4.5 and goal rows in 2.2 when the run lands (`docs/MODEL-AB-RESULTS.md` section 8).
- The user acceptance outcome is "not run". If a session is held before submission, replace A.3 and add its results to A.2.
- Section 4.5 and A.2 results from the Planner are the testers' own notes and were not re-run. Anything the compiler cannot confirm with the tester should be worded "reported".
- The corpus load counts (section 4.4) should be refreshed from the database before submission.
- Delete the "How to use this file" paragraph and this section.
