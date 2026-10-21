# Wireframe validation

Team 83, Alfa Focus Knowledge Assistant.
Validated by Ronith Mugundakumar (requirements owner), 2026-08-21.
Baseline: [`REQUIREMENTS.md`](REQUIREMENTS.md).

> **Historical record (August 2026), about wireframes, not the built system.** The wireframe artboards are not in the repository, and the built UI differs from them in several ways. Not built: the two-step upload with source type and applies-from date (CR-1, UP-2), the `Superseded` status and "upload new version" / "remove from search" menu (CR-4, CR-5, UP-5), the "How Alfa Focus handles it" firm-procedure section (no Corpus B exists), the income-year badge, and the four distinct no-answer states. Built: the client-identifier warning under the chat composer (CR-2, DH-3), signed-in user and role in the sidebar, a document table with statuses `pending`/`processing`/`ready`/`failed` and failure reasons, and recent chats in the sidebar. The section 8 blocker on artboard 04 is resolved in code: the Testing link and card appear only for the `team` role (`frontend/src/components/Sidebar.tsx`, `frontend/src/pages/Home.tsx`) and `/api/testing` rejects other roles. The Home page title still reads "Accounting Knowledge Assistant" rather than the SMSF naming CR-11 asked for. `docs/TRACEABILITY.md`, referred to in section 6, does not exist. Nothing here was validated with Alfa Focus.

## Scope

Validated the UX wireframe set against every requirement in REQUIREMENTS.md that has a screen surface. Requirements that are behavioural, contractual, or process-level are listed in section 6 and are not judged here.

Artboards reviewed:

| # | Artboard |
|---|---|
| 01 | Main chat interface |
| 02 | Document upload page |
| 03 | Chat loading and no-answer states |
| 04 | Main landing / index page |
| 05 | LLM testing and evaluation page |

Artboard 03 was added in the first revision. Artboards 04 and 05 were reviewed as a supplemental set on 2026-08-28.

## Result

**Artboards 01-03: validated.** These screens address the requirements listed in REQUIREMENTS.md sections 4, 5 and 7, subject to the three minor items in section 5.

Round one raised 12 change requests, 5 of which blocked acceptance. All 12 were addressed in the revision. Three minor items remain open and are recorded in section 5; none of them blocks build.

**Artboards 04-05: changes required.** The landing page provides a clear navigation flow, and the testing page supports a basic single-question, two-model comparison. The set does not yet address several mandatory requirements in [`TESTING-PAGE-REQUIREMENTS.md`](TESTING-PAGE-REQUIREMENTS.md), and the landing page conflicts with EV-49 by linking the testing area from the normal product interface. These two artboards are not cleared for build in their current form; the detailed result is in section 8.

## 1. Round one and what changed

| CR | Requirement | Issue raised | Resolution in revision |
|---|---|---|---|
| CR-1 | UP-2 | Upload captured no metadata. Files went straight from drop to the document table. | Two step flow added. Step 2 requires source type (official source or internal firm procedure) with no default, and an applies-from date. Upload stays disabled until both are set. |
| CR-2 | DH-3 | Composer helper text read "Responses may reference uploaded documents." The requirement needs a client identifier warning in that position. | Replaced with "Do not enter client names, TFNs, member numbers or other identifying information", fixed under the composer. Artboard 03 confirms it persists in every state. |
| CR-3 | CH-6, CH-10, CH-11, CH-15, CH-16, CH-17, EC-12 | No not-found state, no refusal state, no outage state. The set designed only the path where the assistant answers. | Artboard 03 added with four mutually exclusive states: no match in documents, outside SMSF scope, refused for privacy or advice, system unavailable. |
| CR-4 | UP-3, UP-4, UP-5 | Statuses were `Processed` and `Uploaded`, which are indistinguishable in meaning. No failure or supersede state. | Four statuses: Processing, Processed, Failed, Superseded. Failure reason shown inline on the row. |
| CR-5 | UP-5, UP-6 | Row overflow menu present but contents undefined. | Menu specified: view document, remove from search, upload new version. |
| CR-6 | CH-2, CH-3, CH-8 | Answer body was a single paragraph. CH-2 requires law and firm procedure never be combined in one sentence. | Answer card split into "Legal position" and "How Alfa Focus handles it" as separate labelled sections. |
| CR-7 | CH-4 | No income year on the answer. | Income year badge added to the answer card header. |
| CR-8 | UP-8, DH-5 | No signed-in user, no sign out, no visible evidence either page sits behind authentication. | Signed-in user and role shown in the rail on both screens, with a sign out control. |
| CR-9 | NF-1 | No state between send and answer. | Loading state added, naming what is being checked. |
| CR-10 | UP-2, UP-8 | Composer attachment icon was a second ingest path that bypassed metadata capture and authorisation. | Removed. Upload is now a single governed path. |
| CR-11 | Client fidelity | Sample content was general financial accounting. The client is SMSF only. | Recast to SMSF throughout. Product renamed to Alfa Focus SMSF Assistant. |
| CR-12 | UP-2 | `Type` column held file format, easy to mistake for corpus. | Renamed to `Format`. `Source Type` and `Applies From` added as separate columns. |

## 2. Chat interface, artboards 01 and 03

| ID | P | Requirement surface | Where it is met |
|---|---|---|---|
| CH-1 | M | Citations openable from the response | Sources block lists each source separately with its own open control. Sources are prefixed by corpus (ATO, Alfa Focus), which maps them to the answer sections above. |
| CH-2 | M | Law and firm procedure in distinct labelled sections | Two labelled regions in the answer card: "Legal position" and "How Alfa Focus handles it". |
| CH-3 | S | Firm procedure shown alongside the legal position | Second region is part of the standard answer card, not an optional extra. |
| CH-4 | M | Income year stated where correctness depends on it | Income year badge on the answer card header, plus the year in the answer body. |
| CH-6 | M | Says so where no source supports an answer | No-match state on artboard 03. |
| CH-8 | S | Consistent answer structure | Fixed region order across the answer card: header and year, legal position, firm procedure, sources. |
| CH-10 | M | States plainly it could not find an answer, no hedging | No-match state reads "I couldn't find this in the approved documents", with no speculative content. |
| CH-11 | M | Distinguishes no source from out of scope | Two visually separate states on artboard 03, different colour treatment and different copy. |
| CH-13 | S | Gives a next step | Each no-answer state carries a suggested next action. |
| CH-15 | M | Does not state member specific figures | Refusal state covers member and client specific questions. |
| CH-16 | M | Does not recommend a course of action for a member | Same refusal state, directing to the approved client advice workflow. |
| CH-17 | S | Refusals follow a consistent format | All four non-answer states share one card frame, so they read as a family. |
| DH-3 | M | Warns against client identifiers at the point of entry | Warning fixed under the composer, present in every state. |
| DH-5 | M | Only authenticated users reach the assistant | Signed-in user and sign out control in the rail. |
| DH-7 | S | Questions and answers retained | Recent conversations list in the rail. |
| EC-1 | M | Out of subject area handled and distinguished from a missing source | Outside scope state, separate from the no-match state. |
| EC-12 | M | Plain failure message, never a partial or unsourced answer | System unavailable state states the question was not processed and that no answer or sources can be shown. |
| NF-1 | S | Answer arrives quickly enough that the user waits | Loading state names what is being checked, so the wait is legible. |
| NF-2 | M | Usable with a short walkthrough | Conventional chat layout, one primary action per screen. |

## 3. Document upload, artboard 02

| ID | P | Requirement surface | Where it is met |
|---|---|---|---|
| UP-1 | M | Upload and index without developer involvement | Drag and drop plus browse, reachable from the rail. |
| UP-2 | M | Corpus and applies-from captured at upload | Step 2 of the upload flow. Source type has no default. Both fields required, upload disabled until complete. |
| UP-3 | M | Uploader sees processing, succeeded or failed | Status column with Processing, Processed, Failed. |
| UP-4 | S | Failure states why in actionable terms | Reason shown on the row, for example "scanned PDF has no readable text". |
| UP-5 | S | New version supersedes rather than deletes | Superseded status, with the row noting it is retained for historical questions. |
| UP-6 | S | Documents listed, individual document withdrawn from search | Document table plus a per row menu with remove from search. |
| UP-8 | M | Only authorised firm users can upload | Signed-in user shown in the rail. Role gating itself is open, see section 5. |
| DH-5 | M | Only authenticated users reach any page | Same rail treatment as the chat screen. |

## 4. Edge cases with a screen surface

| ID | P | Required behaviour | Where it is met |
|---|---|---|---|
| EC-1 | M | Say so, and distinguish from a missing source | Outside scope state. |
| EC-7 | S | Answer without repeating a client identifier | Composer warning is preventive. The refusal state covers the case where one is entered anyway. |
| EC-12 | M | Plain failure message | System unavailable state. |

## 5. Open items

None of these block build. All three are recorded so they are picked up during implementation rather than found in review.

**1. No changed-rule flag on the answer card.** CH-5, EC-2 and EC-10 require an answer to say when it rests on a rule that has changed or a source that predates a known change. The income year badge landed, this marker did not. The document model now supports superseded sources, so an answer can be built on stale material with nothing on the card saying so. This is the only gap of the three that has a requirement behind it at `S` priority or above.

**2. The no-match state does not say what was searched.** CH-12 asks the response to name what was searched and how current that material is, so the user can tell a coverage gap from a currency gap. The current copy says there is not enough approved material, which does not separate the two.

**3. The refusal state does not name where the figure is held.** CH-15 requires the assistant to name where a member specific figure lives rather than only declining. The state directs to the client advice workflow, which is a next step but not an answer to "so where do I get the balance".

Two smaller notes for build:

- Remove from search is styled as a destructive action in the row menu. The wording is correct but the treatment reads as delete, and UP-5 depends on users understanding those documents are kept.
- There is no not-permitted variant of the Documents page. UP-8 and DH-6 are evidenced by the signed-in user but the nav entry is unconditional, so role gating remains an assumption. See section 7.

## 6. Not judged in this validation

Listed so their absence is not read as coverage. Verification for these sits in [`TRACEABILITY.md`](TRACEABILITY.md).

| Requirements | Why not judged here | Verified by |
|---|---|---|
| CH-7, DH-2, DH-4, EC-4, EC-5, EC-6, EC-8, EC-9, EC-11 | Model behaviour with no screen surface | [`EVALUATION.md`](EVALUATION.md) |
| DH-1, DH-8, DH-9 | Contractual, retention policy, and configuration | Client agreement and repository configuration |
| NF-3, NF-4, NF-5, NF-6, NF-7 | Process and non-functional | Evaluation harness and handover documentation |
| CH-9, UP-7 | `C` priority, out of current scope | Deferred |

## 7. Assumptions still open

REQUIREMENTS.md marks these `[ASSUMED]` pending the first client meeting. The wireframes do not resolve them and should not be read as having done so.

| Assumption | Requirements affected | Effect on the design |
|---|---|---|
| Who may upload | UP-8, DH-5 | The Documents page currently shows one permission state. A restricted variant is needed once roles are confirmed. |
| Who may see firm procedure content | DH-6, DH-10 | Answer cards show the firm procedure section unconditionally. If access is role limited, that section needs a hidden state. |
| Retention period for questions and answers | DH-7, DH-8 | Recent conversations implies retention. No period is stated anywhere in the interface. |

Flag these at the client meeting rather than designing roles into the interface ahead of an answer.

## 8. Supplemental validation: landing and testing, artboards 04 and 05

Reviewed 2026-08-28 against [`REQUIREMENTS.md`](REQUIREMENTS.md) and [`TESTING-PAGE-REQUIREMENTS.md`](TESTING-PAGE-REQUIREMENTS.md). This review treats visible controls and states as evidence of what has been designed. It does not infer storage, access control, metric calculation, or other implementation behaviour from a static wireframe.

Status meanings:

- **Aligned** - the required screen surface is visibly designed.
- **Partial** - part of the required interaction is visible, but mandatory states or information are missing.
- **Gap** - the requirement is absent or the design conflicts with it.
- **Not verifiable** - the requirement depends on implementation or stored data and cannot be confirmed from the wireframe.

### 8.1 Artboard 04 - Main landing / index page

| Requirement | Status | Evidence and finding |
|---|---|---|
| NF-2 | Aligned | The page uses three clearly labelled destination cards with one primary action each: AI Assistant, Documents, and LLM Testing & Evaluation. The persistent rail repeats the navigation, so the main tasks are discoverable without training. |
| DH-5 | Partial | A signed-in user, role, and sign-out control are visible. This designs an authenticated state but does not show the unauthenticated or access-denied state, so enforcement is not verified. |
| DH-7 | Partial | Recent conversations are visible in the rail, which designs for retained history. Retention period and access behaviour remain outside what the wireframe can prove. |
| EV-49 | Gap - blocker | The LLM Testing & Evaluation card and the `LLM Testing` rail item link the testing area from the normal product interface. EV-49 requires `/testing` to be restricted to Team 83 and approved reviewers and not linked from the assistant interface. |
| Client and scope fidelity | Gap | The screen is labelled `Accounting Knowledge Assistant` / `Accounting Digital Transformation` and uses generic accounting examples. The validated artboards 01-03 were deliberately recast as the Alfa Focus SMSF Assistant after CR-11. Artboard 04 reintroduces the naming and scope ambiguity that CR-11 closed. |

**Functional assessment:** the landing page is coherent as navigation, but it is not accepted until the testing entry point is removed from the firm-user experience or placed behind an explicit Team 83/reviewer permission state. Product naming and examples must also return to the Alfa Focus SMSF scope.

### 8.2 Artboard 05 - LLM Testing & Evaluation page

| Requirement | Status | Evidence and finding |
|---|---|---|
| EV-1, EV-24 | Partial | One test case can be viewed against Model A and Model B, with answer cards shown side by side. The cards do not visibly expose each model's ordered retrieved chunks and retrieval scores, so the complete per-question comparison required by EV-24 is not designed. |
| EV-2 to EV-6 | Not verifiable | Question ID, question text, expected behaviour, model choice, and answer text are visible, but the wireframe does not show the complete stored record, immutable run ID, chunk snapshots, scorer versions, prompt version, corpus snapshot, or timestamp. |
| EV-7 to EV-20 | Partial | An evaluation-metrics table exists, but the wireframe does not demonstrate every required raw field, denominator, per-claim or per-citation decomposition, not-applicable state, or scorer version. A displayed score is not evidence that the required inputs are stored. |
| EV-21 to EV-23 | Gap - blocker | A reviewer-notes box is present, but there is no four-point human label, no blinded reviewer mode, and no rule requiring a note for a `dangerous` label. |
| EV-25 | Partial | Model identity is correctly visible for a developer comparison. The separate reviewer-labelling view that hides model identity and scorer verdicts is absent. |
| EV-26 to EV-29, EV-37 | Gap | There is no reviewer preference control for Model A, Model B, or tie; no preference-reason field; and no aggregate wins/losses/ties view. |
| EV-30 | Aligned | Model B visibly shows a distinct `No Source` outcome rather than presenting an unsupported answer. This is the required screen surface for `outcome = no_source`. |
| EV-31 to EV-33, EV-39, EV-40 | Gap - blocker | Separate refused, error, incomplete-run, and correctness-not-applicable states are not shown. The wireframe therefore does not establish that no-source, refusal, and system error cannot collapse into the same empty-answer state. |
| EV-34 to EV-36 | Gap | The design has no independent multi-reviewer labels, disagreement state, adjudication, pairwise agreement, Cohen's kappa, or sample size. |
| EV-41 to EV-44 | Gap - blocker | The metrics are presented as one flat table for a test case. There is no per-question-class aggregation, gate beside every gated metric, hard pass/fail treatment for citation resolution, or separation of retrieval metrics from generation metrics. |
| EV-45 to EV-48 | Partial | `Run Again` and `Save Evaluation` are present, but there is no previous-run diff, question-level regression drill-down, class/outcome/model filter, or report export. Saving an evaluation is not the export required by EV-48. |
| EV-49 | Gap - blocker | A signed-in user is shown, but no Team 83/reviewer-only permission state is designed, and artboard 04 exposes the page through normal product navigation. |
| EV-50, EV-51 | Not verifiable | The sample question contains no visible client identifier and a user identity is shown, but identifier screening and reviewer attribution cannot be confirmed from the page. |

**Functional assessment:** the page is functionally understandable for a manual single-question A/B check: select a test, choose two models, run, compare answers and metrics, add notes, and save. It is not yet a functional design for the required evaluation lifecycle because reviewer labelling, distinct outcome states, retrieved-chunk inspection, metric gates and grouping, multi-reviewer adjudication, aggregate reporting, diff/filter/export, and access isolation are missing.

### 8.3 Required wireframe changes before acceptance

1. Remove testing links from the normal assistant/firm-user navigation, or show an explicit Team 83/reviewer-only permission state that makes the page absent for other users (EV-49).
2. Add a blinded reviewer mode with the four human labels, mandatory notes for `dangerous`, and no model identity or scorer verdicts (EV-21 to EV-23, EV-25).
3. Show each model's ordered retrieved chunks, retrieval scores, and scorer verdict details alongside its answer (EV-2 to EV-4, EV-24).
4. Add mutually exclusive `no_source`, `refused`, and `error` states, plus incomplete-run and not-applicable treatments (EV-30 to EV-33, EV-39, EV-40).
5. Add model preference controls for Model A, Model B, and tie, with a reason selector and aggregate wins/losses/ties (EV-26 to EV-29, EV-37, EV-38).
6. Separate retrieval and generation metrics, display each gate beside its value, make citation resolution a hard pass/fail, and add per-class aggregation (EV-41 to EV-44).
7. Add independent reviewer labels, disagreement and adjudication views, pairwise agreement, Cohen's kappa, and sample size (EV-34 to EV-36).
8. Add previous-run comparison, question-level regression drill-down, filters, and report export (EV-45 to EV-48).
9. Restore Alfa Focus SMSF naming and SMSF-specific examples so the landing page remains consistent with the accepted artboards and project scope.

### 8.4 Supplemental decision

**Changes required.** Artboard 04 is usable navigation but conflicts with the testing-access requirement. Artboard 05 demonstrates the core comparison concept but covers only part of the mandatory evaluation workflow. Artboards 04 and 05 are not cleared for build until the blocker items above are represented in the wireframes.

## 9. Sign-off

Artboards 01-03 remain validated against REQUIREMENTS.md as at 2026-08-21 and are cleared for build. Artboards 04-05 were reviewed on 2026-08-28 and require revision before build.

Validation confirms only that requirements have been designed for. It does not confirm they are implemented or met. Rows marked aligned or partial remain unverified until there is a running system to test.
