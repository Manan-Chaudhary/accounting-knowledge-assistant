# Requirements

Team 83 - Alfa Focus Knowledge Assistant. Drafted from the user stories, the client research in [`CLIENT-BRIEF.md`](CLIENT-BRIEF.md), and the domain constraints in [`DOMAIN-PRIMER.md`](DOMAIN-PRIMER.md).

**Status: design document; the client was never met.** Requirements marked `[ASSUMED]` stayed assumed and were never confirmed. This file is what was asked for, not what was built. Implementation status, checked against the code on `main`:

| Area | Status |
|---|---|
| CH-1, CH-4, CH-6, CH-7, CH-10, CH-15, CH-16 | Partly. Enforced only through the system prompt in `app/rag/generator.py`. Numbered citations are verified in code (`app/rag/grounding.py`), and a gate refuses when retrieval returns nothing or the query matches a personal-advice pattern. Quality is measured on the benchmark, not guaranteed |
| CH-2, CH-3, CH-5, CH-9, CH-12, CH-14, CH-17 | Not built. No Corpus B documents exist, no digest, no unanswered-question log, no fixed refusal format beyond the two gate messages |
| UP-1, UP-3, UP-4 | Built. Upload, ingestion via n8n, statuses `pending`/`processing`/`ready`/`failed`, readable `failure_reason`, retry |
| UP-2, UP-5, UP-7 | Not built. Upload takes only a file; `source_label` is set to the filename; no corpus or effective date is recorded; no versioning or preview |
| UP-6 | Partly. Documents can be listed and deleted (admin and staff roles); there is no `withdrawn` or `superseded` state |
| UP-8, DH-5 | Partly. Every route except login, the n8n callback and `/chat` needs a signed-in session, but any signed-in user can upload and `uploaded_by` is stored as the literal `"user"`. `/chat` (Chainlit) is public if `CHAINLIT_AUTH_SECRET` is unset |
| DI-1 to DI-12 | Mostly built in `process_document` (unique id, state, parse, chunk, embed, reprocess without duplicates, retrieval restricted to `ready`). Chunk metadata is `section_heading` only; there are no `corpus`, `effective_*`, `superseded_by` or `chunk_count` columns |
| DH-1, DH-3, DH-4, DH-9 | DH-3 (warning under the chat box), DH-4 (prompt rule 7) and DH-9 (`.env`, gitignored) exist. DH-1 is not verified: generation goes through free-tier providers via LiteLLM with no confirmed no-training terms |
| DH-2, DH-6, DH-7, DH-8, DH-10 | DH-7 partly (chat history is saved). The rest not built; no automated client-identifier detection; security hardening was descoped |
| EC-1 to EC-12 | Prompt-dependent, not individually tested. Failure messages are shown on provider error, but no EC-level tests exist |
| NF-3 | Built in part: 50-case benchmark and harness. NF-4 is not enforced (CI does not run tests or the benchmark) |
| NF-1 | Fails the 8 s P95 target in [`LATENCY-MEASUREMENT-IMPLEMENTATION.md`](LATENCY-MEASUREMENT-IMPLEMENTATION.md) |

Requirements marked `[ASSUMED]` are our inference and need client confirmation before they drive a sprint. They are written broadly on purpose - narrow them once we have met the client, do not invent detail to fill them in.

Priorities are MoSCoW: **M** must have, **S** should have, **C** could have.

Each requirement is written to be testable. If you cannot describe how you would check it, it is not finished - rewrite it rather than passing it on.

## 1. Scope

**In scope:** an internal assistant for Alfa Focus staff that answers questions about superannuation and SMSF rules, and about the firm's own procedures, with sources shown for every answer.

**Out of scope**, and these are deliberate boundaries rather than backlog items:

- Any interface used directly by the firm's clients or fund trustees.
- Calculating a member's personal tax position, balance, or cap.
- Producing a document that leaves the firm without a registered tax agent reviewing it.
- Writing to the firm's practice-management or SMSF administration software.

The reasoning is in [`DOMAIN-PRIMER.md`](DOMAIN-PRIMER.md) section 5: the firm carries the professional liability for anything the assistant produces, so the assistant supports a qualified reviewer rather than replacing one.

## 2. Users

| User | Uses it to | Implication |
|---|---|---|
| SMSF accountant | Check a rule mid-task without leaving the file they are working on | Answers must be fast and skimmable, not essays |
| Senior accountant / principal | Confirm a position, check what staff are being told | Needs to see the source, not the summary |
| Customer service manager | Answer an inbound question from a trustee or referring planner | Needs firm procedure as readily as law |
| Team 83 (development) | Run and inspect evaluations | `/testing`, not the chat interface |

`[ASSUMED]` This role split comes from scraped directory data. Confirm at the first meeting.

## 3. Use cases

| ID | Use case | Primary requirement |
|---|---|---|
| UC-1 | Look up a current threshold, cap, or rate | CH-1, CH-4 |
| UC-2 | Check a rule for a past income year | CH-4 |
| UC-3 | Work out which rules apply to a client scenario | CH-2 |
| UC-4 | Find out how the firm handles a situation | CH-3 |
| UC-5 | Learn what changed recently | CH-9 |
| UC-6 | Add a new document to the knowledge base | UP-1 |
| UC-7 | Ask something the assistant cannot answer | CH-6, EC-1 |

## 4. Chatbot interface

### 4.1 Answering

| ID | P | Requirement |
|---|---|---|
| CH-1 | M | Every substantive claim in an answer cites a source that the user can open from the response. |
| CH-2 | M | An answer separates statements of law from statements of firm procedure into distinct labelled sections and never combines them in one sentence. |
| CH-3 | S | Where the firm has a documented procedure relevant to the question, the answer includes it alongside the legal position. |
| CH-4 | M | Any answer whose correctness depends on the income year states that year explicitly. |
| CH-5 | S | Where the question rests on a rule that has since changed, the answer says so and gives the current position. |
| CH-6 | M | Where no source supports an answer, the assistant says so rather than answering. See 4.2. |
| CH-7 | M | The assistant does not confirm the existence or contents of a ruling, determination, or provision that is not in its sources, including when the user asserts that it exists. |
| CH-8 | S | Answers are structured consistently so a user can find the part they need without reading the whole response. |
| CH-9 | C | A periodic digest summarises what changed in the source material, without the user having to ask. |

CH-7 exists because the most damaging failure available to this system is agreeing with a plausible but invented citation. A user who trusts one such answer will trust the next.

### 4.2 When the assistant does not know

The behaviour required by CH-6, stated in full because it is the checklist item this card was raised for.

| ID | P | Requirement |
|---|---|---|
| CH-10 | M | The assistant states plainly that it could not find an answer. It does not hedge, speculate, or answer from general knowledge. |
| CH-11 | M | The response distinguishes "no source covers this" from "this is outside what I do". These are different problems with different fixes. |
| CH-12 | S | The response names what was searched and how current that material is, so the user knows what the gap actually is. |
| CH-13 | S | The response gives a next step - who to ask, or where to look. |
| CH-14 | C | Unanswered questions are logged so gaps in the knowledge base can be found and filled. |

CH-14 turns failures into a work queue. Without it, the same gap is rediscovered by a different person every month.

### 4.3 Refusals

| ID | P | Requirement |
|---|---|---|
| CH-15 | M | The assistant does not state a figure specific to a member or fund, and instead names where that figure is held. |
| CH-16 | M | The assistant does not recommend a course of action for a member; it sets out the rules bearing on the decision and leaves the recommendation to the practitioner. |
| CH-17 | S | Refusals follow a consistent format, so users learn to recognise them rather than reading each one as a failure. |

CH-15 is not a limitation we chose. Member-specific figures depend on data the assistant does not hold, so any figure it produced would be a guess presented with a citation - the worst combination available.

## 5. File upload interface

| ID | P | Requirement |
|---|---|---|
| UP-1 | M | An authorised user can upload a document and have it become searchable without developer involvement. |
| UP-2 | M | Upload requires the uploader to record whether the document is authority or firm procedure, and the date from which it applies. |
| UP-3 | M | The uploader can see whether a document processed successfully, is still processing, or failed. |
| UP-4 | S | A failed upload states why it failed in terms the uploader can act on. |
| UP-5 | S | Uploading a newer version of an existing document marks the old version superseded rather than deleting it, so past-year questions still work. |
| UP-6 | S | Uploaded documents can be listed, and an individual document can be withdrawn from search. |
| UP-7 | C | The uploader can preview how a document was split before it is indexed. |
| UP-8 | M | Only authorised firm users can upload. |

UP-2 is the requirement most likely to be dropped under time pressure and the one that will cost most if it is. Without the date and the corpus, a document cannot be filtered correctly and will surface against the wrong questions.

### 5.1 Document management and ingestion lifecycle

Uploaded documents must pass through a defined ingestion lifecycle before they become available to the knowledge base. This ensures incomplete or failed documents are not returned during retrieval and that retrieved chunks can always be traced back to their original source.

The document lifecycle is:

`Upload → Validation → Parsing → Chunking → Embedding → Storage / Indexing → Ready`

If any required stage fails, the document moves to a `failed` state and must not be made available for retrieval.

| ID | P | Requirement |
|---|---|---|
| DI-1 | M | Every uploaded document must be assigned a unique document identifier before processing begins. |
| DI-2 | M | The system must record the current ingestion state of each document. |
| DI-3 | M | Required document information must be validated before processing begins. |
| DI-4 | M | Valid documents must be parsed to extract usable textual content. |
| DI-5 | M | Parsed document content must be divided into retrievable chunks before embeddings are generated. |
| DI-6 | M | Every chunk must retain a reference to its parent document and its position within that document. |
| DI-7 | M | An embedding must be generated for every valid retrievable chunk before it becomes available to retrieval. |
| DI-8 | M | A document must only become available for retrieval after all required ingestion stages have completed successfully. |
| DI-9 | M | Failed or incomplete documents and chunks must not be returned by the retrieval system. |
| DI-10 | M | If validation, parsing, chunking, embedding, or storage fails, the document must be marked as `failed` and a readable failure reason must be retained. |
| DI-11 | S | A processing failure affecting one document should not prevent other valid documents from continuing through ingestion. |
| DI-12 | S | Reprocessing a document should not create duplicate retrievable chunks for the same document and chunk position. |

#### Document processing states

| State | Meaning |
|---|---|
| `pending` | The upload has been accepted and is waiting for processing. |
| `processing` | One or more ingestion stages are currently running. |
| `ready` | Processing has completed successfully and the document is available for retrieval. |
| `failed` | Processing could not be completed and the document is excluded from retrieval. |
| `superseded` | A newer version has replaced the document for current queries while the older version is retained for historical questions. |
| `withdrawn` | The document remains retained but is intentionally excluded from retrieval. |

#### Document-level metadata

The system must retain enough metadata to manage each document throughout its lifecycle and support correct filtering during retrieval.

| Field | Purpose |
|---|---|
| `document_id` | Unique identifier for the document. |
| `filename` | Original uploaded filename. |
| `corpus` | Identifies whether the document is authority or firm procedure. |
| `effective_from` | Date from which the document applies. |
| `effective_to` | Date until which the document applies, where known. |
| `status` | Current ingestion state. |
| `uploaded_by` | Identifies the authorised user who uploaded the document. |
| `uploaded_at` | Records when the document was uploaded. |
| `failure_reason` | Readable explanation when processing fails. |
| `superseded_by` | Reference to a newer document version where applicable. |
| `chunk_count` | Number of retrievable chunks created from the document. |

#### Chunk-level metadata and source attribution

Each retrievable chunk must retain enough information to identify where the retrieved content came from.

| Field | Purpose |
|---|---|
| `chunk_id` | Unique identifier for the chunk. |
| `document_id` | Reference to the original parent document. |
| `chunk_index` | Position of the chunk within the document. |
| `content` | Text used during retrieval and answer generation. |
| `embedding` | Vector representation used during semantic retrieval. |
| `page_or_section` | Page, section, heading, or other source location where available. |
| `source_title` | Human-readable name of the original source. |
| `source_url` | Openable source location where available. |
| `corpus` | Identifies whether the source is authority or firm procedure. |
| `effective_from` | Supports time-aware retrieval where applicable. |
| `effective_to` | Supports retrieval of historical material where applicable. |

Every retrieved chunk must remain linked to its parent document so that the system can provide source attribution and citations for generated answers.

#### Upload and processing failure scenarios

The ingestion process must account for:

- missing required upload information;
- unsupported or invalid file types;
- corrupted or unreadable documents;
- documents where no usable text can be extracted;
- parsing failures;
- chunking failures;
- embedding generation failures;
- database or storage failures;
- duplicate processing attempts.

If processing cannot be completed, the document must remain visible with a `failed` status and a readable failure reason. Incomplete content from a failed document must not be available to retrieval.

## 6. Data handling and privacy

The constraints behind these are set out in [`DOMAIN-PRIMER.md`](DOMAIN-PRIMER.md) section 5. Two are worth stating here because they are absolute rather than negotiable: professional guidance is that client data must not go into public AI tools, and under the TPB code an error the practitioner relied on is the practitioner's breach regardless of what produced it.

| ID | P | Requirement |
|---|---|---|
| DH-1 | M | No client data is sent to any third-party service that does not carry contractual terms prohibiting training on it. |
| DH-2 | M | The assistant answers questions about rules, and needs no client names, tax file numbers, or member numbers to do so. |
| DH-3 | M | The interface tells users not to enter client identifiers, at the point where they would enter one. |
| DH-4 | S | Where a user includes an identifier anyway, the assistant answers the underlying question without repeating it back. |
| DH-5 | M | Only authenticated firm users can reach the assistant or any of its pages. |
| DH-6 | M | Firm procedure content is not reachable by anyone outside the firm. |
| DH-7 | S | Questions and answers are retained so the firm can show what the tool said and what was done with it. |
| DH-8 | S | Retention has a defined period, agreed with the client rather than assumed by us. |
| DH-9 | M | Credentials and connection strings are held in environment configuration and never committed. |
| DH-10 | C | Firm procedure content can be restricted by role, if the client wants some material limited. |

`[ASSUMED]` DH-8 and DH-10 both depend on client policy we have not seen. DH-8 in particular must not be guessed - a retention period we invent could conflict with the firm's own obligations.

## 7. Edge cases

| ID | P | Situation | Required behaviour |
|---|---|---|---|
| EC-1 | M | Question is outside the assistant's subject area | Say so, and distinguish it from a missing source (CH-11) |
| EC-2 | M | Question assumes a superseded figure or rule | Correct the assumption before answering |
| EC-3 | M | Question asks about a past income year | Answer for that year, using the material that applied then |
| EC-4 | M | User cites a source that does not exist | Say it cannot be found; do not speculate about its contents |
| EC-5 | S | Sources disagree, or a position is genuinely unsettled | Present both and identify which carries more authority |
| EC-6 | S | Question requires several rules together | Cover each, or state which parts were not covered |
| EC-7 | S | Question contains a client identifier | Answer the rules question without repeating the identifier |
| EC-8 | S | Question is ambiguous | Ask one clarifying question rather than guessing |
| EC-9 | S | Only weak or commentary-level sources support the answer | Answer, and say the support is weak and what should be checked |
| EC-10 | S | Relevant material exists but predates a known change | Answer, and flag that the source may not reflect the current position |
| EC-11 | C | Question is asked in the firm's internal shorthand | Resolve known internal terms; otherwise ask |
| EC-12 | M | The model or database is unavailable | Show a plain failure message; never a partial or unsourced answer |

EC-12 matters more than its length suggests. A degraded answer during an outage is indistinguishable from a normal answer and carries none of the guarantees above.

## 8. Non-functional

| ID | P | Requirement |
|---|---|---|
| NF-1 | S | A typical question returns a complete answer quickly enough that the user waits for it rather than switching tasks. |
| NF-2 | M | The assistant is usable by an accountant with no training beyond a short walkthrough. |
| NF-3 | M | Answer quality is measured against a benchmark set rather than asserted. See [`EVALUATION.md`](EVALUATION.md). |
| NF-4 | M | Changes to prompts, retrieval, or sources are re-measured before merge. |
| NF-5 | S | The firm can add and correct source material without the development team. |
| NF-6 | S | The system can be handed over to a firm with no IT staff, with documentation to match. |
| NF-7 | C | Running costs are visible and predictable. |

NF-1 is deliberately not a number. We do not yet know what users will tolerate, and a target invented now would either be missed or meaningless. Set it once we have watched someone use it.

NF-6 follows from the client's apparent size ([`CLIENT-BRIEF.md`](CLIENT-BRIEF.md) section 3). Anything requiring ongoing engineering will stop working after handover.

## 9. Open questions for the client

Each of these blocks or reshapes a requirement above. Full context and framing in [`CLIENT-MEETING-QUESTIONS.md`](CLIENT-MEETING-QUESTIONS.md).

| # | Question | Affects |
|---|---|---|
| 1 | Is the practice SMSF-only, or is there a general tax book alongside it? | Scope, section 1 |
| 2 | Do written procedures exist, or is firm knowledge held in people's heads? | CH-3, UP-2, and the whole firm-procedure corpus |
| 3 | What is the firm's position on client data and AI tools? | DH-1, DH-8 |
| 4 | Which SMSF platform is used, and does it have an API? | UP-1, and whether integration is in scope at all |
| 5 | Who may upload, and who may see firm procedure content? | DH-5, DH-6, DH-10, UP-8 |
| 6 | How long should questions and answers be retained? | DH-7, DH-8 |
| 7 | Is there a question the firm would never want answered by a tool? | CH-15, CH-16, section 7 |

Question 2 is the one to resolve first. If firm procedure is not written down anywhere, a significant share of the requirements above describe a corpus that does not yet exist, and creating it becomes project work rather than an ingestion task.

## 10. Traceability

Requirement IDs are stable. When one changes materially, supersede it with a new ID rather than editing it in place, so that references from user stories, board cards, and test cases do not silently point at something else.

Every `M` requirement should have at least one corresponding check in [`EVALUATION.md`](EVALUATION.md) before it is called done. Where no check exists yet, the requirement is agreed, not verified - and the difference should be visible in the sprint review rather than assumed.
