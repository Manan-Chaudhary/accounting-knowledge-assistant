# Citation behaviour rules

Team 83, Alfa Focus Knowledge Assistant.
Drafted 2026-10-07 by Ronith Mugundakumar.
Surfaces: the citation markers in an assistant answer, the source chips under it, the source viewer opened from a chip, and the copied answer. Code: `app/rag/retriever.py`, `app/rag/generator.py`, `app/chainlit/chainlit_app.py`, `frontend/src/pages/Chat.tsx`, `app/evaluation/harness.py`.

Defines the marker format the model writes and which variants the parser accepts, how each marker maps to a retrieved passage and its document, what a source chip shows, what clicking it opens, what the user sees when a source is unmatched, superseded, withdrawn, deleted or cannot be opened, how citations behave in a refusal, and what the copy button produces. Requirement IDs are `CB-n` and are stable, per the traceability rule in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10.

**Status: proposed, not built.** Nothing in sections 4 to 11 exists in the code today (section 2). Requirements marked `[ASSUMED]` need team or client confirmation before they drive a build. The largest are the decision to flag rather than remove an unmatched citation (CB-17) and the decision that a no-source refusal shows no chips (CB-58).

Priorities are MoSCoW: **M** must, **S** should, **C** could.

## 1. Purpose and scope

CH-1 (M) says every substantive claim cites a source "that the user can open from the response." Today a user sees `[1]` as plain text with nothing to open. This document fixes the rules so UX (R122) can draw the chips and viewer and Dev (R99, R105, R101, R141) can build the parser, click-through, copy and validation against one definition.

**In scope:** the marker format, marker-to-source mapping, unmatched markers, chip contents, the viewer and the "open original" control, source states and their wording, citations in retained answers, citations in refusals, and the copied answer.

**Out of scope**, with the document that owns each:

- When the assistant must answer, say it cannot answer, or decline, and the wording of those answers. That is card R119 (grounding and refusal rules) and [`PROMPTS.md`](PROMPTS.md) section 2. R119 also owns the final rule on how citations behave in a refusal; section 10 here is only the citation-side default until R119's document settles it.
- The answer structure (sections, headings, income-year badge). That is I-4 in `docs/ITERATION-AND-EXPLORATION.md` and [`PROMPTS.md`](PROMPTS.md), which is the source of truth for the prompt.
- Markdown rendering of the answer body. That is I-7 in `docs/ITERATION-AND-EXPLORATION.md` and card R99.
- What a citation shows after its document is deleted. That is DD-35 to DD-37 in `docs/DOCUMENT-DELETE-REQUIREMENTS.md`. Section 8 points to them and does not redefine them.
- Storing turns. That is SS-40 and SS-41 in [`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md). Section 9 states only what a stored turn must hold for citations.
- Adding document metadata (corpus, dates, section headings, URL, `superseded_by`). That is UP-2, UP-5, the metadata tables in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 5.1, and card R124 for section headings. This document says what the chip shows when a field exists and when it does not.

References to `docs/ITERATION-AND-EXPLORATION.md` (findings F7, F9, F13, items I-4, I-7, and PR #65) are to a file that is on the unmerged branch `docs/sprint3-priorities`, not yet on `main`.

## 2. What exists today

| Component | Current state | Verified in |
|---|---|---|
| Marker the prompt asks for | Rule 1: "Every substantive claim must cite a chunk in your context using [n]." Rule 3's example ends "$2.1 million [1]." No form is given for citing two sources at once. | `app/rag/generator.py` lines 45-61; [`PROMPTS.md`](PROMPTS.md) section 1 |
| Context block | Numbered from 1 in fused rank order. Each block is `[n]`, then `Source:` (source label or filename), `File:`, `Document ID:`, `Chunk:` (the chunk index) and `Content:`. No title, section, corpus, tier, date or URL. With no chunks, the context is an instruction to state that no source was found. | `app/rag/retriever.py` `format_retrieved_context`, lines 369-400 |
| Number of blocks | `DEFAULT_TOP_K = 6`. PR #65 reportedly lowers the chat default to 3 (finding F9); not verified here. | `app/rag/retriever.py` line 18 |
| Source list kept for the UI | None. `generate_response` calls `retrieve_context`, which returns the formatted string only. The chunk list is discarded, so nothing downstream knows what `[n]` points at. | `app/rag/generator.py` lines 166-167 |
| What the chat sends | `cl.Message(content=reply_text)`. No elements, metadata or source list. The chat calls the non-streaming `generate_response`. | `app/chainlit/chainlit_app.py` lines 117-128 |
| Prior turns | Earlier answers, with their markers, are passed back to the model as history. | `app/chainlit/chainlit_app.py` lines 111-122; `app/rag/generator.py` lines 176-178 |
| Saved answers | `/api/chat/threads/{id}/messages` returns `id`, `type`, `name`, `output` and `createdAt` per step. No sources. | `app/routes/chat_history.py` lines 79-133 |
| Chat page | No marker parsing. Body text renders in a plain `<p>`, so `[1]` shows literally. A "Sources" or "References" heading is parsed for Markdown links written by the model; the context carries no URL, so there are none to write (finding F13). | `frontend/src/pages/Chat.tsx` lines 39-81, 139-191 |
| Citation validation | No `validate_citations` exists in `app/`. [`RAG-DESIGN.md`](RAG-DESIGN.md) sections 6 and 7 (`generator.validate_citations` in the section 7 request path) and [`EVALUATION.md`](EVALUATION.md) section 4 describe one. | grep of `app/` |
| Harness scoring | `CITATION_PATTERN = \[(\d+)\]` and a second pattern for fullwidth lenticular brackets (U+3010, U+3011) that allows text after the number. A marker is invalid if `n < 1` or `n > chunk_count`. The first pattern cannot match `[1, 2]`, so comma lists are neither counted nor validated. | `app/evaluation/harness.py` lines 35-37, 316-355 |
| Document fields | `filename`, `source_label`, `storage_path`, `status`, `failure_reason`, `uploaded_by`, `uploaded_at`. No title, corpus, tier, URL, effective dates or `superseded_by`. Chunks have no section. Upload sets `source_label` to the filename. | `app/db/models.py`; `app/db/schema.sql`; `app/routes/upload.py` line 54 |
| Chunking | Fixed 2000-character windows with 200 overlap. Reprocessing deletes a document's chunks and inserts new ones, so chunk ids change. | `app/services/document_service.py` lines 54-83, 135-162 |
| Opening a stored file | No endpoint serves a file or a signed URL. Storage is used for upload and for download during processing only. | `app/routes/*.py`; `app/services/storage_service.py`; `app/services/document_service.py` line 116 |
| Auth on `/chat` paths | The middleware treats any path containing `/chat` as public. That includes `/api/chat/threads/...`, which checks the session itself inside each handler. | `app/main.py` lines 50-51; `app/routes/chat_history.py` lines 21, 86, 143 |
| Privacy notice text | The code prompt's rule 7 asks for "[Notice: Client identifiers omitted per privacy guidelines]." [`PROMPTS.md`](PROMPTS.md) rule 7 instead says "Note once that identifiers are not needed here." The two have drifted; CB-3 covers the code's bracketed form. | `app/rag/generator.py` line 83; [`PROMPTS.md`](PROMPTS.md) line 80 |

### 2.1 What the models actually write

Counted from `model_answer` in `benchmarks/results/*.jsonl`, 22 cases per Groq run.

| Form | Example | Seen in |
|---|---|---|
| `[n]` | `... small business [1].` | Every run |
| Adjacent `[n][m]` or `[n] [m]` | `[1][2][3]` | qwen3.8-27b (9 answers), gpt-oss-120b (2) |
| Comma list `[n, m]` | `[1, 2, 3]` | gemini-3.8-flash in `dense.jsonl` (4 of 12 answered; 7 of its 19 rows are `provider_unavailable`) and the sample file (2 of 4), qwen3.8-27b (2), gemini-3.6-flash (1) |
| Fullwidth brackets | U+3010, `6`, U+3011, sometimes adjacent | gpt-oss-20b (5 answers: EVAL-004, 006, 010, 012, 021), gpt-oss-120b (2: EVAL-007, 009) |
| `[0]` | `... flow-chart [0].` | gpt-oss-120b EVAL-001, gpt-oss-20b EVAL-001, gemini-3.6-flash EVAL-004 |
| Number outside the list | `[7]` and `[16]` with 6 blocks | qwen3.8-27b EVAL-007 `[7]`, EVAL-014 `[16]`, EVAL-015 `[7]` |
| Markers in table cells | `\| ... \| [2] \|` | gpt-oss-120b EVAL-003, 011; gpt-oss-20b EVAL-001, 003, 013 |
| Range between markers | `context [1]-[6]` (written with an en-dash) | qwen3.8-27b EVAL-017 and EVAL-022, both refusals |
| Bracketed text that is not a marker | `[s 165-85]` | gpt-oss-120b EVAL-017 |
| Narrow no-break space (U+202F) before a marker | `flow-chart` U+202F `[0]` | gpt-oss-120b and gpt-oss-20b |

Two out-of-range numbers match integers printed in the context block: in EVAL-007 every block has `Document ID: 7`, and in EVAL-014 the fourth retrieved chunk has `Chunk: 16`. EVAL-015's `[7]` matches neither. That the model copied the document id or chunk index is `[ASSUMED]`, not shown; CB-10 addresses it either way.

Refusals are not marker-free: gpt-oss-120b EVAL-021 and qwen3.8-27b EVAL-017, EVAL-021 and EVAL-022 are scored as refusals and still contain markers.

## 3. Terms

- **Marker:** the citation number in the answer text, for example `[2]`.
- **Source list:** the ordered list of passages sent to the model as context for one answer. Position 1 is block `[1]`.
- **Source chip:** the control under an answer that names one cited source and opens it.
- **Source viewer:** the panel a chip opens.
- **Passage:** the text of one retrieved chunk.

## 4. Marker format

| ID | P | Requirement |
|---|---|---|
| CB-1 | M | The canonical marker is `[n]`: ASCII square brackets around a decimal integer with no spaces, where n is a position in that answer's source list. Two or more sources are cited as adjacent markers, `[1][3]`. This refines rule 1 in [`PROMPTS.md`](PROMPTS.md), which names `[n]` but gives no multi-source form; the prompt wording change belongs to I-4. |
| CB-2 | M | The parser accepts these variants and normalises each to canonical markers before mapping: (a) comma lists `[1, 2]` and `[1,2]` become `[1][2]`; (b) fullwidth lenticular brackets (U+3010, U+3011) around digits become `[n]`, including adjacent pairs; (c) fullwidth brackets with text after the number, which the harness pattern already allows, become `[n]` using the number only. Any whitespace before a marker, including U+202F, is left as it is. |
| CB-3 | M | Bracketed text is not a marker unless its content is only digits or a CB-2 list of digits. Not markers: `[s 165-85]`, the privacy notice `[Notice: Client identifiers omitted per privacy guidelines]` that rule 7 of the prompt asks for, Markdown links `[text](url)`, footnotes `[^1]`, and checkboxes `[ ]` and `[x]`. These render as written. |
| CB-4 | S | A bracketed four-digit year followed by a space and an upper-case court or tribunal code, such as `[2019] HCA 12`, is a medium-neutral case citation, not a marker. `[ASSUMED]` None appears in the current result files, but Australian tax answers cite cases in this form, and without this rule the year would be flagged as an unmatched citation. |
| CB-5 | M | Ranges are never expanded. In `[1]-[6]` (qwen3.8-27b EVAL-017) only 1 and 6 are markers. A bracketed range such as `[1-3]` is not a marker and renders as written. Expanding a range would attach sources the model may not have used. |
| CB-6 | M | `[0]` is a marker and is always unmatched, because numbering starts at 1. It is never shifted to `[1]`, because guessing the model's intent can attach the wrong source. |
| CB-7 | M | Markers in table cells, list items, headings, bold and italic text are converted. Markers inside inline code or fenced code blocks are not converted and not counted. `[ASSUMED]` No answer in the result files has a marker in code. |
| CB-8 | M | The harness and the chat parser recognise the same set of markers. Today the harness misses comma lists (section 2), so the variants in CB-2 must be added to `harness.py`. `citation_format_standard` keeps reporting any non-canonical form as false, because normalisation is a safety net, not a licence. |
| CB-9 | S | The prompt change under I-4 is judged by `citation_format_standard` and `citation_valid` before and after, per [`PROMPTS.md`](PROMPTS.md) section 6. |
| CB-10 | S | Each context block makes its citation number the only bare integer a model could mistake for one. `Document ID` and `Chunk` are removed from the block or relabelled as internal, for example `Internal ref: doc 7 / part 16`. `[ASSUMED]` This reduces out-of-range markers; it is measured by `citation_valid`, owned by I-4 and R141. |

## 5. Mapping markers to sources

| ID | P | Requirement |
|---|---|---|
| CB-11 | M | Numbering is scoped to one answer. `[n]` means position n in the source list sent to the model for that answer, in the order `format_retrieved_context` numbered it. A number never refers to another answer's sources. |
| CB-12 | M | The server keeps the source list for each answer. For each position it holds the chunk id, document id, chunk index, the passage text, and the chip fields of section 6 as they were when the answer was given. |
| CB-13 | M | Chips and the viewer are built only from the server's source list. Titles, URLs or source lists written by the model are never turned into links or chips. A model can write a plausible URL; it cannot change the source list. |
| CB-14 | M | The UI receives the source list for an answer with the answer. `[ASSUMED]` The list is sent before the first token, since retrieval finishes before generation starts. R127's event format currently puts sources in the final event; if it stays that way, CB-27 applies until that event arrives. |
| CB-15 | M | A marker is matched when 1 <= n <= the length of the source list. Every other number, including 0, is unmatched. |
| CB-16 | M | A matched marker renders as a clickable inline marker showing its number, and opens the same viewer as its chip. |
| CB-17 | M | An unmatched marker stays in the text where the model put it and renders as a flag: a non-link, non-button element whose text is `[n?]` instead of `[n]`, with the accessible name "Unmatched citation n" and the tooltip in CB-46. It is never silently removed and never re-pointed at another source. `[ASSUMED]` This settles R141's "removed or flagged" in favour of flagged: removing it hides the one signal that a claim is unsupported, and the accountant is the person who must check. |
| CB-18 | M | Each distinct matched number produces one chip. Repeated markers for the same number all open that chip's source. |
| CB-19 | M | Chips are listed in ascending number and keep their original numbers. If an answer cites `[1]` and `[3]` but not `[2]`, the chips are 1 and 3. Numbers are never closed up, so the text and the chips always agree. |
| CB-20 | M | Retrieved passages that the answer never cites do not get chips. `[ASSUMED]` |
| CB-21 | C | A collapsed "Also searched (k)" list names the retrieved passages the answer did not cite. |
| CB-22 | M | Two numbers that point at different passages of one document are two chips. Each shows the document name and its own section or passage (CB-33). |
| CB-23 | M | The server-side check in R141 uses the same source list and the same patterns as the parser, runs on the final answer text, and stores with the turn which numbers were matched and which were not. Its result is the production counterpart of the citation resolution gate (1.00) in [`EVALUATION.md`](EVALUATION.md) section 4 and EV-43 in [`TESTING-PAGE-REQUIREMENTS.md`](TESTING-PAGE-REQUIREMENTS.md). |
| CB-24 | M | A marker in an earlier answer in the thread is resolved only against that earlier answer's source list. |
| CB-25 | S | When earlier answers are passed to the model as history (SS-24), their markers are removed first, so the model cannot repeat an old number that now points at a different block. `[ASSUMED]` Owned by I-4 and R141. |

### 5.1 While the answer streams

The chat does not stream today (section 2). R127 builds the streaming endpoint and R99 must parse during the stream.

| ID | P | Requirement |
|---|---|---|
| CB-26 | M | An incomplete marker at the end of the streamed text (`[`, `[1`, `[1,` or an open fullwidth bracket) is held back and not shown until it closes or the stream ends. A marker, once converted, is never converted back. This is what "without flicker" in R99 means for markers. |
| CB-27 | M | A closed marker that arrives before the source list renders as a neutral pending marker: numbered, not clickable, not flagged. It is matched or flagged when the list arrives. No marker is flagged as unmatched before the list is known. |
| CB-28 | M | If the stream ends with a marker still open, the held text is shown as written. If the stream fails, EC-12 applies and no partial answer is kept; error states are card R123. |

## 6. Source chip contents

Chips appear in a "Sources" row under the answer. Their visual design is R122's.

| ID | P | Requirement |
|---|---|---|
| CB-29 | M | Each chip shows, in this order: the number, the document name, the source type, the date, the section or passage, and a status tag when the source is not current (section 8). |
| CB-30 | M | Document name is the recorded title where one exists, else `source_label`, else `filename`. Today every chip will show the filename, because upload copies it into `source_label`. On the chip, a name longer than 40 characters shows its first 37 characters followed by "...". The full name shows in the viewer and in the accessible name. `[ASSUMED]` 40 characters. |
| CB-31 | M | Source type is "Official source" for corpus A (authority) and "Internal procedure" for corpus B (firm practice), the same labels as the document filters in R104 and R130. Where no corpus is recorded, which is every document today, it is "Type not recorded". It is never inferred from the filename. |
| CB-32 | M | Date is, in order of preference: the income year(s) recorded on the cited chunk ("Income year 2025-26", or "Income years 2024-25, 2025-26"); else the document's applies-from date ("From 2025-07-01", or "From 2024-07-01 to 2025-06-30" when an end date is recorded); else "Date not recorded". The upload date is never shown in its place, because it says when the firm added the file, not when the rule applied. `[ASSUMED]` YYYY-MM-DD format, matching DD-36. |
| CB-33 | M | Section is the chunk's recorded section heading or path (`page_or_section` in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 5.1, `section_path` in [`RAG-DESIGN.md`](RAG-DESIGN.md) section 4, kept by R124). Where none is recorded, it is "Passage k", where k is the chunk index plus one. A page number is shown only if one is stored. |
| CB-34 | M | The source type is shown as text on the chip itself ("Official source" or "Internal procedure"), never by colour or icon alone, and the viewer for an internal procedure says "Firm practice. Not a legal requirement." This is the chip-level side of CH-2; it lets a reader spot a firm procedure cited under the law section. |
| CB-35 | C | Official source chips show the authority tier ("Tier 1" to "Tier 4", [`RAG-DESIGN.md`](RAG-DESIGN.md) section 4) once it is stored. |
| CB-36 | M | Each chip is a keyboard-focusable button with the accessible name "Source n: name, type, date". Each matched inline marker is focusable with the name "Citation n". Enter and Space open the viewer. |

## 7. What clicking opens

| ID | P | Requirement |
|---|---|---|
| CB-37 | M | Clicking a chip or a matched inline marker opens the source viewer as a panel on the chat page. The page URL does not change, and at a browser width of 1024 pixels or more the message list stays visible and scrollable while the panel is open. `[ASSUMED]` The 1024-pixel threshold; layout below it is R122's. |
| CB-38 | M | The viewer shows every chip field in full, the passage with the cited text highlighted, and the "Open original" control (CB-41). |
| CB-39 | M | The passage shown is the text stored with the answer (CB-12), not the chunk read again later. Chunk ids and boundaries change when a document is reprocessed (section 2) or re-chunked by R124 and R125, so a live lookup could show a different passage from the one the model saw. |
| CB-40 | S | Where the chunks either side of the cited one still exist and the stored passage still equals the live chunk at the same index, the viewer shows them unhighlighted around it. Text repeated by chunk overlap is shown once. Otherwise only the stored passage is shown. |
| CB-41 | M | "Open original": for an official source with a recorded URL, the control opens that URL in a new tab and names the site ("Open on ato.gov.au"). For an uploaded file, it opens the stored file through a signed URL (CB-42) in a new tab; PDF and TXT open in the browser and DOCX downloads. Where neither exists, CB-51 applies. |
| CB-42 | M | The signed URL for a stored file is created on each click by an endpoint that checks the signed-in session itself, expires after `[ASSUMED]` 10 minutes, and is never stored in chat history or in copied text (DH-5, DH-6). The endpoint path must not contain `/chat`, because `app/main.py` treats any such path as public. |
| CB-43 | M | The highlight is shown in the viewer's text only. The original opens at its start, and the viewer says "The original opens at the start. The highlighted passage is from the text extracted from it." No page or offset is stored, so the system never claims to jump to the passage in a PDF or DOCX. |
| CB-44 | M | The viewer closes with Esc and with a visible close button, and focus returns to the chip or marker that opened it. |
| CB-45 | M | Opening a source never re-runs retrieval or regenerates the answer (SS-35). |

## 8. Missing, superseded and unavailable sources

The chip fields come from the snapshot stored with the answer (CB-12). The status tag is checked when the answer is shown, so a reopened answer reports what has happened to its sources since. Wording is exact; R122 may restyle it but not reword it without a change here.

| ID | P | Case | How it is known | What the user sees |
|---|---|---|---|---|
| CB-46 | M | Unmatched marker | CB-15 | Flag in the text (CB-17). Tooltip: "This citation does not match a source retrieved for this answer. Check this claim before relying on it." Above the chips: "1 citation in this answer could not be matched to a retrieved source and is marked in the text." For more than one: "{k} citations in this answer could not be matched to a retrieved source and are marked in the text." |
| CB-47 | M | Answer with no matched marker that is not a refusal | No CB-15 match, and the turn's outcome (CB-68) is `answered` | Not accepted behaviour: CH-1 and EC-12 win (section 12), and R141's gate replaces such an answer with the no-source refusal before it is shown. Only if one reaches the UI anyway (the gate not yet built, or a saved answer from before it) does the UI show, instead of chips: "This answer does not cite a retrieved source. Do not rely on it without checking the documents." R106 or R141 testing logs any occurrence as a defect. |
| CB-48 | M | Superseded | `superseded_by` set on the document (UP-5) | Tag "Superseded". Viewer: "Superseded by {newer document name} from {YYYY-MM-DD}. This answer cited the earlier version." with "Open current version", which opens the newer document in the viewer with no highlight. Without a date: "Superseded by {newer document name}." Not testable until UP-5 adds `superseded_by`, the same as DD-31 to DD-34. |
| CB-49 | M | Withdrawn | Document status `withdrawn` (UP-6) | Tag "Withdrawn". Viewer: "Withdrawn from search on {YYYY-MM-DD}. The passage below is the text this answer cited." "Open original" stays available to signed-in users. Not testable until UP-6. |
| CB-50 | M | Deleted | Document row gone; deletion record (DD-43) | As DD-36, unchanged: "This document was deleted on YYYY-MM-DD", or "This document is no longer available" with no deletion record. Tag "Deleted". No "Open original". `[ASSUMED]` The stored passage is still shown, as part of what the tool said (DH-7); see open question 4. |
| CB-51 | M | No original recorded | No URL and no `storage_path` | Viewer: "No original file or link is recorded for this source. The cited passage is shown below." No "Open original" control. |
| CB-52 | M | Original cannot be opened now | Signed URL request or storage fetch fails | Viewer: "The original could not be opened. The cited passage is shown below." with "Try again". No tag on the chip, because the failure may be brief. Never shown as deleted. |
| CB-53 | M | Source details cannot be loaded | Viewer request fails | Viewer: "This source could not be loaded. Try again." with "Try again". The chip keeps its stored fields. |
| CB-54 | S | Official link failed its last check | `url_last_ok` older than the last check ([`RAG-DESIGN.md`](RAG-DESIGN.md) section 4) | Viewer: "The official page could not be reached when last checked on {YYYY-MM-DD}." The link is still offered. Not testable until a link checker exists. |
| CB-55 | M | Answer saved with no source list | Every answer saved before this work, and any later save that lost it | Markers render as plain, unclickable text and no chips show. Under the answer: "Sources were not saved for this answer, so its citations cannot be opened." The answer is not re-resolved against the current corpus (SS-35). |

## 9. Retained answers

| ID | P | Requirement |
|---|---|---|
| CB-56 | M | A stored turn (SS-40) holds the full source list of CB-12 and the matched or unmatched result of CB-23, not only the cited sources, so a reopened answer can redraw its chips and flags exactly. It is not a cascading foreign key to `documents` (DD-37). |
| CB-57 | M | A reopened answer shows the same markers, chips, flags and passages as when it was given (SS-35, SS-41, DD-35). Only the status tags of section 8 may change. |
| CB-67 | M | Any endpoint that returns stored passages or source lists checks the signed-in session inside its own handler and returns not found for a thread the user does not own (SS-36). The middleware does not protect it: `app/main.py` lines 50-51 treat any path containing `/chat` as public, which already covers `/api/chat/threads/{id}/messages`, the route that will carry CB-56 data. That route checks the session itself today (`app/routes/chat_history.py` lines 86-99) and must keep doing so. Any new endpoint for sources or passages has no `/chat` in its path. |

Storage: a full source list at today's `DEFAULT_TOP_K = 6` and 2000-character chunks is up to about 12,000 characters of passage text per turn, about half that at 3 chunks. `[ASSUMED]` acceptable at the firm's volume; if not, uncited positions may store only their ids and fields without passage text, since CB-15 needs only the list length and CB-21 is a C.

## 10. Citations in a refusal

Card R119 (Ronith, grounding and refusal rules) owns which answers are refusals, their wording, and the final rule on citations in a refusal. CB-58 to CB-60 and CB-68 are the citation-side default until R119's document is agreed, and that document may override them. Where it does, it names the CB ID it replaces.

| ID | P | Requirement |
|---|---|---|
| CB-68 | M | The server records an outcome with each turn: `answered`, `refused_no_source` or `refused_with_rule`. R141's gate sets it when the gate produces the refusal itself. For a refusal the model wrote, `[ASSUMED]` the server sets it by matching the refusal wording of [`PROMPTS.md`](PROMPTS.md) section 2 (the patterns already in `app/evaluation/harness.py` lines 41-55): `refused_with_rule` when the answer has a BASIS IN LAW section as in the member-specific and personal-advice templates, otherwise `refused_no_source`. The UI reads the outcome; it never decides it. |
| CB-58 | M | A turn with outcome `refused_no_source` shows no chips and no "closest sources" list, even if its text contains markers. Precedence: this rule beats CB-16 and CB-18. Its markers render as plain text, neither clickable nor flagged, and are not counted by CB-46. `[ASSUMED]` Passages shown under "I could not find authority for this" read as support for something the assistant has just said it cannot support. What was searched (CH-12) is stated in the refusal text. |
| CB-59 | M | A turn with outcome `refused_with_rule` states a general rule with `[1]` under BASIS IN LAW. Its markers and chips follow sections 4 to 8 like any answer. |
| CB-60 | M | Stray markers in a no-source refusal are a prompt or grounding defect, not something to display. qwen3.8-27b EVAL-017 and EVAL-022 both write `[1]-[6]` to say the context is irrelevant. `[ASSUMED]` R141 strips markers from a `refused_no_source` answer before it is stored, and R119 decides whether the prompt forbids them. |

## 11. Copying an answer

R101 adds the copy button. This is what it copies.

| ID | P | Requirement |
|---|---|---|
| CB-61 | M | The copy is plain text: the answer with Markdown syntax removed (headings as their own lines, list items as "- ", bold and italic marks dropped, table rows kept with " \| " between cells), and every marker in canonical form (CB-2 variants normalised). |
| CB-62 | M | After the answer comes a blank line, the line "Sources", and one line per chip in ascending number: "[n] {document name}, {source type}, {date}, {section}". An official source with a recorded URL adds " - {URL}". |
| CB-63 | M | No link is copied for an internal procedure or an uploaded file. A signed URL expires, and pasting it into an email would carry firm content outside the system (DH-6). |
| CB-64 | M | Unmatched markers stay in the copied text as `[n?]`, and each adds a source line "[n] Unmatched citation: no retrieved source." |
| CB-65 | M | A source with a status tag carries it in its line: ", superseded", ", withdrawn", or ", deleted {YYYY-MM-DD}". |
| CB-66 | M | Copying an answer covered by CB-55 copies the text followed by "Sources were not saved for this answer." |

## 12. Conflicts with existing documents

| Existing text | Conflict | Which wins |
|---|---|---|
| [`RAG-DESIGN.md`](RAG-DESIGN.md) section 6: the answer ends with a model-written "SOURCES - [n] title, publisher, effective from, URL" | CB-13 builds sources only from the server's list | CB-13, for anything shown as a link or chip. Whether the prompt still asks for a SOURCES section is decided in [`PROMPTS.md`](PROMPTS.md) under I-4. If it does, the UI hides that section in favour of the chips, so the user never sees two source lists that disagree. `[ASSUMED]` |
| `frontend/src/pages/Chat.tsx` parses Markdown links under a "Sources" heading | Same as above | CB-13. R99 replaces that parsing. |
| R141 checklist: unmatched citations "removed or flagged" | Leaves the choice open | CB-17: flagged. |
| R127: "the cited sources" in the final stream event | CB-14 prefers the full source list before the first token | Neither is broken. CB-27 covers a list that arrives last; sending it first is better for the user and is `[ASSUMED]`. If the final event carries only cited sources, it must also carry the source list length (or the unmatched numbers), because CB-15 cannot tell `[7]` is unmatched without it. |
| [`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md) SS-40: a turn stores "the sources cited" | CB-12 and CB-56 store the full retrieved list with passage text | CB-56 extends SS-40 and does not contradict its purpose. Cited sources alone cannot redraw unmatched flags (CB-15 needs the list length) or CB-21, and SS-41 needs the passage as it was. Storage cost and a lighter option are under CB-67. |
| [`REQUIREMENTS.md`](REQUIREMENTS.md) CH-1 (every claim cites a source the user can open) and EC-12 (never an unsourced answer) vs CB-47 | CB-47 describes an answer shown with no source | CH-1 and EC-12 win. An answer with no matched marker is blocked by R141 and replaced by the no-source refusal. CB-47 is only the safe display if one leaks through, and it is logged as a defect, never accepted. |
| CH-1 vs CB-50 (deleted), CB-51 (no original recorded), CB-52 (original cannot be opened now) | Each shows a chip whose original file or link cannot be opened | CB wins, with this reading of CH-1 `[ASSUMED]`: the source the user opens is the cited passage in the viewer, stored with the answer (CB-39). That holds in all three cases, so the claim stays checkable. The original is extra evidence. CB-51 for an official source is a data defect, because [`RAG-DESIGN.md`](RAG-DESIGN.md) section 4 requires `source_url` for corpus A. If the client answers no to open question 4, a deleted source's passage is hidden and CB-50 no longer meets CH-1 for that old answer; DD-36 then wins for retained answers, because CH-1 governs an answer when it is given, not after its source is removed. |
| [`EVALUATION.md`](EVALUATION.md) lines 192 and 216: fullwidth markers are ones "the chat UI would not render" | Today the UI renders no marker of any kind | Not a rule conflict. After R99, both forms render (CB-2), and the metric still counts the fullwidth form as non-standard (CB-8). |

## 13. Test mapping for R106

R106 (Zekun) tests R99 and R101 (Shihong). The fixtures are real answers from `benchmarks/results/`, replayed through the parser as fixed text with a 6-item source list, so the tests do not depend on a model call.

| # | Check | Fixture | Pass when | IDs |
|---|---|---|---|---|
| 1 | Chips for five different answers | gpt-oss-120b EVAL-011, gpt-oss-20b EVAL-004, qwen3.8-27b EVAL-014, gemini `sample_gemini_3_8_flash.jsonl` EVAL-002, gpt-oss-120b EVAL-001 | One chip per distinct matched number, ascending, numbers unchanged | CB-2, CB-18, CB-19 |
| 2 | Markdown renders around markers | Same five | Tables, lists, headings and bold render; markers in table cells are clickable | CB-7, I-7 |
| 3 | Variants normalised | gpt-oss-20b EVAL-004 (fullwidth), gemini EVAL-002 (comma list), qwen3.8-27b EVAL-014 (adjacent) | Each becomes canonical clickable markers | CB-2 |
| 4 | Unmatched markers flagged | qwen3.8-27b EVAL-014 `[16]`, gpt-oss-120b EVAL-001 `[0]` | Shown in place as `[16?]` and `[0?]`, not clickable, CB-46 tooltip and count line shown, no chip | CB-6, CB-15, CB-17, CB-46 |
| 5 | Not-a-marker text untouched | gpt-oss-120b EVAL-017 `[s 165-85]`; a test string with the rule 7 privacy notice | Renders as written, no chip | CB-3 |
| 6 | Range not expanded; refusal suppresses chips | (a) test string "The rule applies [1]-[3]." with outcome `answered`; (b) qwen3.8-27b EVAL-017 `[1]-[6]` with outcome `refused_no_source` | (a) chips 1 and 3 only; (b) no chips, `[1]` and `[6]` shown as plain text, no unmatched notice | CB-5, CB-58, CB-60, CB-68 |
| 7 | Streaming | gpt-oss-120b EVAL-011 replayed in 1 to 5 character pieces, with a split inside `[1]` | No raw `[1` shown, no marker changes state twice, final render equals check 1 | CB-26, CB-27 |
| 8 | Copy | gpt-oss-120b EVAL-011 and qwen3.8-27b EVAL-014 | Plain text pastes cleanly into Outlook and Word; "Sources" list as CB-62; `[16]` line as CB-64; no signed URL | CB-61 to CB-64 |
| 9 | Saved answer with no source list | Any thread saved before R99 | CB-55 wording, no chips; copy as CB-66 | CB-55, CB-66 |

Check 7 is not applicable until R127 lands; record it as such rather than as a pass. Section 8 states other than CB-46 and CB-55 belong to R105's testing, not R106. No test card for R105 appears in the Sprint 3 Planner export; one is needed, with a tester other than Zekun, who builds R105.

## 14. Open questions

| # | Question | For | Affects |
|---|---|---|---|
| 1 | Should an unmatched citation be flagged (proposed) or removed? | Team, then client | CB-17, CB-46, R141 |
| 2 | Should a no-source refusal list the closest passages searched? Proposed no. | Client | CB-58, R119 |
| 3 | Is the extracted passage enough, or do users need the original file opened at the passage? Opening at the passage needs page numbers stored at ingest. | Client | CB-41, CB-43, R124 |
| 4 | When a document is deleted, may its cited passage still show in old answers? | Client | CB-50, DD-36 |
| 5 | Dates on chips: YYYY-MM-DD, or "1 July 2025"? | Client | CB-32, DD-36 |
| 6 | Signed URL lifetime: is 10 minutes acceptable? | Team | CB-42 |
| 7 | Can R127 send the source list before the first token? | Zekun | CB-14, CB-27 |

## 15. Handoff to UX and Dev

- **R122, Manan Chaudhary (UX):** sections 6 to 8. Draw the inline marker in matched, pending (CB-27) and unmatched (CB-17) states; the chip with all CB-29 fields, the two source types (CB-31, CB-34) and the four status tags; the viewer with the passage highlight, "Open original", and every message in section 8; the CB-55 and CB-47 notices; keyboard focus (CB-36, CB-44).
- **R99, Shihong He (parser):** sections 4, 5 and 5.1. The supported marker format for the card's deliverable note is CB-1 to CB-7. Build from the server source list, never model-written links (CB-13).
- **R105, Zekun Liu (viewer):** sections 7 and 8, plus the new signed-URL endpoint (CB-42).
- **R101, Shihong He (copy):** section 11.
- **R106, Zekun Liu (test):** section 13.
- **R141, Zekun Liu (grounding):** CB-17, CB-23, CB-25, CB-47, CB-60 and the turn outcome in CB-68.
- **R119, Ronith Mugundakumar (grounding and refusal rules):** owns the final refusal rules and may override CB-58 to CB-60 and CB-68, naming the ID replaced.
- **Thread messages route (SS-40 build):** CB-56, CB-67.
- **R127, Zekun Liu (streaming):** CB-14, CB-27, open question 7.
- **I-4 owner:** CB-1 prompt wording, CB-10 context block labels, CB-25 history, and the SOURCES decision in section 12, recorded in [`PROMPTS.md`](PROMPTS.md).

## 16. Traceability

| Source | Covered by |
|---|---|
| R117 checklist: marker format | Section 4, CB-1 to CB-10 |
| R117 checklist: chip contents (name, section, type, date) | Section 6, CB-29 to CB-36 |
| R117 checklist: missing, superseded, unavailable | Section 8, CB-46 to CB-55 |
| R117 description: marker to chunk mapping; what clicking opens | Section 5, CB-11 to CB-28; section 7, CB-37 to CB-45 |
| REQUIREMENTS.md CH-1, cite every claim, openable from the response | CB-13, CB-16, CB-41 |
| REQUIREMENTS.md CH-2, law and firm practice kept apart | CB-31, CB-34 |
| REQUIREMENTS.md CH-4, income year stated | CB-32 |
| REQUIREMENTS.md CH-6, CH-10, CH-12, no-source behaviour | CB-58, CB-60, CB-68 |
| REQUIREMENTS.md CH-1 and EC-12 vs unsourced or unopenable sources | CB-47, section 12 |
| REQUIREMENTS.md DH-5, DH-6, DH-7 | CB-42, CB-63, CB-50, CB-56 |
| REQUIREMENTS.md UP-2, UP-5, UP-6 | CB-31, CB-32, CB-48, CB-49 |
| CHAT-SESSION-REQUIREMENTS.md SS-35, SS-36, SS-40, SS-41 | CB-45, CB-55, CB-56, CB-57, CB-67 |
| DOCUMENT-DELETE-REQUIREMENTS.md DD-35 to DD-37 | CB-50, CB-56, CB-57 |
| EVALUATION.md citation resolution gate; TESTING-PAGE-REQUIREMENTS.md EV-43 | CB-8, CB-23 |
| ITERATION-AND-EXPLORATION.md F7, F13, I-4, I-7 | Section 2.1, CB-10, CB-13, section 12 |
| R99, R101, R105, R106, R122, R127, R141 | Section 15 |

Nothing here is verified as built. These are proposed rules for behaviour that does not exist yet; each `M` needs a check before it is called done, per [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10.
