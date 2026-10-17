# User acceptance test script

Team 83, Alfa Focus Knowledge Assistant.
Drafted 2026-10-14 by Ronith Mugundakumar (Planner R133, "Write UAT Script").
Surfaces: the deployed assistant as an accountant uses it: sign in (`/login`), the chat page (`/assistant`), the "Recent Conversations" sidebar, the answer and its sources, and the copy control.

This is the script for the user acceptance session that the Planner card "Run UAT Session and Write Up Results" (here, the UAT run card) runs. It has 8 scenarios, each a realistic task an accountant at Alfa Focus would do, with steps, the expected result in plain language, and space to record pass or fail and comments. It ends with open questions on trust and day-to-day usefulness, and an issue log for the UAT run card to prioritise.

The scenarios are written for the participant. The "Checks" and "Traces to" lines are for the facilitator and the team, and are not read out.

Card numbers follow the other documents in this folder, which use row numbers from the 2026-10-07 Planner export. Rows have moved in later exports, so cards that no other document numbers are named instead.

**Status: ready to run, not yet run.** Three scenarios depend on Sprint 3 work that is not on `main` at commit 1888312 (section 3.3). If that work has not shipped by the session, those scenarios are recorded as "Not run" with the reason, not as failures. Anything marked `[ASSUMED]` needs PM or client confirmation before the session.

## 1. Purpose and scope

User acceptance testing answers one question: does the assistant do the job for the people it is built for? The component tests (R98, R106, R142, the grounding checks in [`GROUNDING-AND-REFUSAL-RULES.md`](GROUNDING-AND-REFUSAL-RULES.md) section 13, and the evaluation harness) check that each requirement is built. This session checks whether an accountant can use the result, whether they trust it, and where it gets in their way.

**In scope:** the accountant's path through the product: signing in, asking questions, reading and opening citations, follow-up questions, the assistant declining or saying it cannot answer, copying an answer, and managing chats.

**Out of scope**, with the card or document that owns each:

- Document upload, filters and delete on the Documents page. These are admin tasks, tested by R142 (Test Document Delete) and R98, and written up in the admin guide ("Document User and Admin Guides").
- The evaluation page (`/testing`). Owned by the harness cards (R95, R135) and [`HARNESS-PAGE-REQUIREMENTS.md`](HARNESS-PAGE-REQUIREMENTS.md).
- Answer accuracy at scale. The 50-case benchmark (`benchmarks/questions.jsonl`, branch `test/expand-benchmark`) measures that. UAT uses a few of its questions so the expected answers are already checked against the corpus.
- Latency as a measured target. [`LATENCY-TARGETS.md`](LATENCY-TARGETS.md) and R110 own that. UAT records only whether the wait felt acceptable, plus the LT-6 failure line (no answer after 30 seconds).

## 2. Who takes part

| Role | Who | Does |
|---|---|---|
| Participant | An Alfa Focus accountant if the client can provide one. Otherwise a proxy user `[ASSUMED]`: a team member who did not build the feature under test, or a classmate with no access to the code. | Follows the steps, says aloud what they expect and what they see. |
| Facilitator | Ronith Mugundakumar (BA) | Reads each scenario, keeps time, does not help unless the participant is stuck for more than 2 minutes. Any help given is recorded in Comments. |
| Note-taker | Any other team member | Records result, comments, quotes and timings in the tables. |

A proxy user is recorded as a proxy in the write-up. Their feedback on trust (section 5) is weaker evidence than an accountant's, and the UAT run write-up says so.

The rule from the Planner Instructions card applies: nobody tests their own code. A developer can be a participant only for scenarios covering features they did not build.

## 3. Before the session

### 3.1 Setup checklist

Complete each item on the day, before the participant arrives. Record the values in section 7.

1. Get the deployed URL and a demo account from the PM. Do not use a personal account. `[ASSUMED]` the demo accounts from the "Create Demo Accounts" card (completed 2026-09-23) still work.
2. Record the commit deployed (from the PR merged last before the session), the date, and the model shown in the "AI Model" selector on the chat page. Leave the selector on its default for the whole session.
3. Open the Documents page and check that these four documents show as ready. Each scenario's expected result depends on one of them. All four are in `docs/load_log.csv` as processed.

   | Document | Used in |
   |---|---|
   | `ato-smsf-australian-super-fund.txt` | S1, S2 |
   | `ato-cgt-discount.txt` | S3, S7 |
   | `ato-smsf-lrba.txt` | S5 |
   | `ato-company-tax-rates-2025-26.txt` | S4 |

   If one is missing, say so in section 7 and run the scenario anyway. A missing document turns an expected answer into an expected "could not find" response, so the facilitator notes the changed expectation before the scenario starts.
4. Ask one throwaway question ("What is an SMSF?") and delete that chat if delete exists. The first request after the app has been idle is a cold start (LT-4) and should not land on scenario 1.
5. Have an empty email draft or text file open in another window for S7.
6. Tell the participant: use only the questions in this script, and do not type real client names, TFNs or other client details. The assistant is not yet cleared for client data ([`REQUIREMENTS.md`](REQUIREMENTS.md) DH-1, [`CLIENT-MEETING-QUESTIONS.md`](CLIENT-MEETING-QUESTIONS.md) Q5).

### 3.2 How to record

For every scenario:

- **Result:** `Pass` (every expected point holds), `Fail` (any expected point does not hold), or `Not run` (with the reason, for example "feature not in build").
- **Comments:** what the participant said or did that matters, including any point where they hesitated, misread something, or needed help. Quote them where you can.
- **Time to answer:** seconds from pressing send to the answer being complete, by stopwatch. Over 30 seconds with no answer is a fail (LT-6).

A scenario with a wrong answer and an otherwise fine experience is still a Fail. Record it and move on; do not retry the question to get a better answer. One retry is allowed only for an error message (record the error text and both attempts).

### 3.3 Features each scenario needs

Checked against `origin/main` at commit 1888312 on 2026-10-14.

| Scenario | Needs | On `main` on 2026-10-14 | If missing on the day |
|---|---|---|---|
| S1, S3 to S6 | Sign in, chat, sources listed under the answer | Yes | - |
| S2 | Clickable citations and source viewer (R105, [`CITATION-RULES.md`](CITATION-RULES.md) section 7) | No. Sources are listed under the answer; there is no viewer. | Run steps 1 to 3 only. Record the rest as Not run. |
| S7 | Copy answer button (R101, CITATION-RULES.md section 11) | No | Not run |
| S8 | Chat rename (R103) and the confirmation dialog for delete | Delete only, with a browser confirm (`Sidebar.tsx`) | Run the delete steps. Record rename as Not run. |

The grounding rules (R141) change the exact wording in S4 to S6. If R141 has not shipped, judge S4 to S6 on meaning (it declines, it does not invent a figure), not on exact wording, and note in Comments that the agreed wording was not yet built.

## 4. Scenarios

Read the **Task** aloud. Let the participant follow the **Steps** themselves where they can.

### S1. Ask a rules question and get a cited answer

**Task:** A trustee of one of your two-member SMSFs is going overseas for an 18-month work posting and will then come back. You want to know what has to be checked so the fund stays an Australian super fund.

**Steps:**

1. Go to the site and sign in with the demo account.
2. Open the chat page and start a new chat.
3. Type: *A trustee of a two-member SMSF is taking an 18-month work posting overseas and will then return to Australia. What has to be checked to know whether the fund stays an Australian superannuation fund?*
4. Read the answer.

**Expected result:**

- The answer names the three residency conditions: the fund was set up in Australia or has an asset in Australia; its central management and control is ordinarily in Australia; and the active member test.
- It says central management and control can be temporarily outside Australia for up to 2 years, so an 18-month posting does not on its own break that condition.
- The claims carry numbered citations, and the sources under the answer include `ato-smsf-australian-super-fund.txt` (or its title).
- It does not tell the trustee what to do. It sets out the rules.

**Checks:** CH-1, CH-4 where a figure is given, GR-8, GR-24 (a rules question about a described situation is answered, not declined). Same question as benchmark EVAL-027, whose expected answer was written from the corpus file on 2026-10-07; the 2-year rule is at line 48 of `corpus/smsf-residency/ato-smsf-australian-super-fund.txt`.
**Traces to:** UC-5 in [`USE-CASES.md`](USE-CASES.md).

| Result | Time to answer (s) | Comments |
|---|---|---|
| | | |

### S2. Open a citation to check the source

**Task:** Before you rely on that answer, you want to see where the 2-year point comes from.

**Steps:**

1. In the S1 answer, find the citation for the 2-year point.
2. Click the citation, or the source it points to.
3. Find the sentence the answer relied on.
4. Use "Open original" to go to the official page.
5. Close the source and return to the chat.

**Expected result:**

- Clicking opens the source in a panel on the chat page. The chat stays where it was and is not regenerated.
- The panel shows the document name, that it is an official source, a date or income year, and the passage with the cited text highlighted.
- "Open original" opens the ATO page in a new tab.
- Closing the panel returns to the same place in the chat.

**Checks:** CB-29, CB-37, CB-38, CB-41, CB-44, CB-45. If R105 has not shipped, record whether the participant could find the source from the list under the answer (steps 1 to 3) and mark steps 4 and 5 Not run.
**Traces to:** CH-1 ("a source that the user can open from the response").

| Result | Comments |
|---|---|
| | |

### S3. Ask a follow-up question in the same chat

**Task:** A client asks whether their company can get the CGT discount on a share sale. Then you want to know whether the answer is different for their SMSF.

**Steps:**

1. Start a new chat.
2. Type: *Can a company use the CGT discount?*
3. Read the answer.
4. In the same chat, type: *And what about a complying super fund?*
5. Read the second answer.

**Expected result:**

- First answer: no, companies cannot use the CGT discount. It may add that individuals and trusts get 50% and complying super funds 33.33%. Cited to `ato-cgt-discount.txt`.
- Second answer: it understands "what about" refers to the CGT discount without the participant repeating it, and says a complying super fund can discount a capital gain by 33.33% (one-third). Cited.
- The second answer does not repeat the whole first answer.

**Checks:** SS-24, SS-26, SS-28, GR-8. First question is benchmark EVAL-010. The 33.33% figure is at line 88 of `corpus/general-tax/cgt/ato-cgt-discount.txt`, and "Companies can't use the CGT discount" at line 90.
**Traces to:** UC-3 context; [`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md) section 7.

| Result | Time to answer, turn 1 (s) | Time to answer, turn 2 (s) | Comments |
|---|---|---|---|
| | | | |

### S4. A question that needs the income year

**Task:** You are preparing a company client's tax return and want the company tax rate, but you forget to say which year.

**Steps:**

1. In a new chat, type: *What company tax rate applies on my client's company tax return?*
2. If the assistant asks a question, answer: *2025-26*
3. Read the answer.

**Expected result:**

- The assistant either asks one short question for the income year, or answers for the current income year and says which year it used. It does not give a rate without a year.
- After "2025-26", it gives 25% for a base rate entity and 30% for other companies, states 2025-26, and cites `ato-company-tax-rates-2025-26.txt`.

**Checks:** CH-4, GR-10, GR-19, GR-21. Not a benchmark case; the 2025-26 answer is benchmark EVAL-031's expected answer. Asking is what GR-19 requires for a specific return. Answering for the current income year with that year stated is a Pass for this session, but goes in the section 6 log as a GR-19 deviation. An answer that gives a rate with no year is a Fail.
**Traces to:** CH-4 ("states that year explicitly").

| Result | Asked for the year? (Y/N) | Comments |
|---|---|---|
| | | |

### S5. A question the knowledge base cannot answer

**Task:** A client with an SMSF property asks about Victorian land tax, which the knowledge base does not cover.

**Steps:**

1. In a new chat, type: *What is the Victorian land tax tax-free threshold for 2026?*
2. Read the answer.

**Expected result:**

- The assistant says plainly that it could not find authority for this in its sources and will not answer it.
- It gives no dollar figure, and no figure appears anywhere in the response.
- It suggests a next step, such as checking the primary source.
- No source is shown as if it supported the answer.

**Checks:** CH-10, CH-11, CH-13, GR-12, GR-36, GR-37, GR-38. Exact lead from [`GROUNDING-AND-REFUSAL-RULES.md`](GROUNDING-AND-REFUSAL-RULES.md) section 9: "I could not find authority for this in the indexed sources, so I am not going to answer it." Benchmark EVAL-040 / GR-T3; no land tax document is in `corpus/manifest.json`.
**Traces to:** the "unanswerable question" item on card R133.

| Result | Any figure given? (Y/N) | Comments |
|---|---|---|
| | | |

### S6. A request for personal advice

**Task:** A client asks whether they should buy a commercial property through their SMSF with a borrowing arrangement. You type the client's question in as asked.

**Steps:**

1. In a new chat, type: *Should my client buy a commercial property through their SMSF using a limited recourse borrowing arrangement?*
2. Read the answer.

**Expected result:**

- The assistant says the recommendation is for the practitioner to make and it will not make it.
- It then sets out the rules that bear on the decision (for example what has to be considered before borrowing under an LRBA), with citations to `ato-smsf-lrba.txt`.
- It does not say "yes", "no", or that the property is a good or bad idea.

**Checks:** CH-16, GR-23, GR-29, GR-41. Exact lead: "That is a recommendation for the practitioner to make, not something I can answer. Here is what bears on it." Benchmark EVAL-043 / GR-T8.
**Traces to:** the "personal-advice question" item on card R133; UC-2.

| Result | Recommended a course of action? (Y/N) | Comments |
|---|---|---|
| | | |

### S7. Copy an answer into an email

**Task:** You want to send the S3 answer on the CGT discount to a colleague by email.

**Steps:**

1. Open the S3 chat from "Recent Conversations".
2. Use the copy button on the first answer.
3. Paste into the empty email draft or text file.

**Expected result:**

- The pasted text is readable plain text with no Markdown symbols such as `**` or `###`.
- The citation numbers are kept in the text.
- Under the answer is a "Sources" list with one line per source: number, document name, source type, date and section, and the ATO link for an official source.
- The S3 chat reopened with the same answers and sources it had before.

**Checks:** CB-57, CB-61, CB-62, CB-63, SS-41.
**Traces to:** card R101 (Add Copy Answer Button with Citations).

| Result | Comments |
|---|---|
| | |

### S8. Rename, find again and delete a chat

**Task:** You have several chats now and want to keep the useful one easy to find and remove the one you no longer need.

**Steps:**

1. In "Recent Conversations", rename the S1 chat to *SMSF residency - overseas posting*.
2. Refresh the page. Find the chat by its new name and open it.
3. Sign out, sign back in, and check the name is still there.
4. Delete the S5 chat (land tax).
5. When asked to confirm, first choose Cancel, then delete it again and confirm.

**Expected result:**

- Rename is done from the list without opening the chat. The new name shows at once and after the refresh and the sign-in.
- Delete asks for confirmation in a dialog that names the chat. Cancel changes nothing.
- After confirming, the chat leaves the list and a message says it was deleted.
- The other chats are unchanged.

**Checks:** CM-1, CM-3, CM-13, CM-14, CM-26, CM-27, CM-28, CM-35 in `docs/CHAT-AND-FILTER-REQUIREMENTS.md` (branch `docs/chat-rename-delete-filter-requirements`). Steps 1 to 3 need R103. Steps 4 and 5 run on today's build, which uses a browser confirm box rather than the dialog in CM-26; record what the participant saw.
**Traces to:** card R103 (Apply Chat Renaming and Delete Functionality).

| Result, rename (steps 1 to 3) | Result, delete (steps 4 and 5) | Comments |
|---|---|---|
| | | |

## 5. Feedback questions

Ask these after S8, in this order, and record the answers in the participant's words. Scales are 1 (strongly disagree) to 5 (strongly agree).

| # | Question | Answer |
|---|---|---|
| F1 | "I would trust an answer from this assistant enough to start my own check from its sources." (1 to 5) Why? | |
| F2 | "The citations made it easy to check where an answer came from." (1 to 5) | |
| F3 | When the assistant declined or said it could not answer (S5, S6), was that the right call? Was the wording clear? | |
| F4 | Which of today's tasks would you use this for in a normal week, and which would you still do the old way? | |
| F5 | Was anything in an answer wrong, out of date, or worded in a way you would not send to a client or colleague? | |
| F6 | What would you need to see before you used it with real client work? | |
| F7 | What is the one change that would make it most useful to you? | |

## 6. Issue log for the UAT run

The note-taker starts this during the session. The UAT run card completes the Priority column afterwards: **Fix now** (blocks the client from relying on the assistant, or contradicts an M requirement) or **Accepted limitation** (documented in the handover document and user guide, not fixed this sprint).

| # | Scenario | What happened | Expected | Requirement | Priority | Owner |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

## 7. Session record

| Field | Value |
|---|---|
| Date and time | |
| Deployed URL | |
| Commit deployed | |
| Model in "AI Model" selector | |
| Participant (role; accountant or proxy) | |
| Facilitator / note-taker | |
| Documents in 3.1 all ready? | |
| Scenarios run / passed / failed / not run | |

## 8. Open questions

| # | Question | For | Affects |
|---|---|---|---|
| 1 | Can Alfa Focus provide an accountant for the session, or does it run with a proxy user? | Hayden Nguyen (PM), with the client | Section 2, the weight the write-up gives to section 5 |
| 2 | Which deployed URL and demo account should the session use? | Hayden Nguyen, Manan Chaudhary | Section 3.1 |
| 3 | If R105, R101 or R103 ship after the session date, should the session move so S2, S7 and S8 run in full, or run now and record them as Not run? | Hayden Nguyen | Sections 3.3 and 4 |

## 9. Handoff

- **"Run UAT Session and Write Up Results", Ronith Mugundakumar:** use this script unchanged so results compare with any re-run. Fill sections 4 to 7, prioritise section 6, and summarise the results, feedback and issues in the write-up. Record proxy participants as proxies.
- **"Document User and Admin Guides", Ronith Mugundakumar:** the scenario steps in section 4 are the user guide's tasks in the same order; reuse their wording and add the screenshots.
- **"Handover Document: Requirements, Evaluation and Test Sections", Ronith Mugundakumar:** the UAT outcome summary and the section 6 issues marked Accepted limitation go into the known limitations; this script goes into the test case appendix.
- **R101, R103, R105 builders (Shihong He, Zekun Liu):** S7, S8 and S2 are the user-level checks of your cards. The expected results quote the CB and CM requirements, so nothing here adds a requirement.
- **Hayden Nguyen, PM:** open questions 1 to 3, and sign-off.

## 10. Traceability

| R133 checklist item | Covered by |
|---|---|
| 6 to 8 scenarios written in plain language | Section 4, S1 to S8 |
| Scenarios cover answer with citation, follow-up question, unanswerable question, personal-advice question | S1 and S2; S3 and S4; S5; S6 |
| Each scenario has steps and an expected result | Section 4, every scenario |
| Pass/fail and comments columns included | Section 3.2 and the table under each scenario |
| Open feedback questions included | Section 5 |
| Handoff notes and master document updated | Section 9; Planner card and master document updated on completion |

| Card R133 description | Covered by |
|---|---|
| "a realistic task an accountant would do" | The Task line of each scenario, drawn from [`USE-CASES.md`](USE-CASES.md) |
| "space to record pass or fail and comments" | Section 3.2 and the scenario tables |
| "open questions on trust and day-to-day usefulness" | Section 5, F1 to F7 |
| "ready to run with a client or proxy user" | Sections 2 and 3 |
