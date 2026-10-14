# Chat rename, chat delete and document list filter requirements

Team 83, Alfa Focus Knowledge Assistant.
Drafted 2026-10-07 by Ronith Mugundakumar.
Surfaces: the "Recent Conversations" list in the sidebar (`frontend/src/components/Sidebar.tsx`), the thread routes in `app/routes/chat_history.py`, and the "Uploaded Documents" list on the Documents page (`frontend/src/pages/Documents.tsx`) with `GET /api/documents` (`app/routes/upload.py`).

Defines two small features: renaming and deleting a conversation from the chat history sidebar, and filtering the documents list by processing status and source type. For each it covers where the control appears, validation, confirmation, what is stored or removed, persistence after refresh, empty results, and how a tester checks it. Requirement IDs are `CM-n` for chat rename and delete and `DF-n` for document list filters. Both are stable, per the traceability rule in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10.

**Status: drafted after a partial first build.** Chat delete already exists on main; rename and filters do not (section 2). Requirements marked `[ASSUMED]` need client or team confirmation. The largest is the interim rule in section 4.1 that a user's delete hides a conversation and keeps its records, because [`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md) SS-17 and SS-44 do not allow a user to erase history before the client sets a retention period.

Priorities are MoSCoW: **M** must, **S** should, **C** could.

## 1. Purpose and scope

**In scope:** renaming and deleting one's own conversation from the sidebar, the server endpoints behind those actions, filtering the documents list by status and source type, and the empty and error states of both.

**Out of scope**, with the document that owns each:

- Thread lifecycle, history content and the retention period. [`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md) SS-1 to SS-44, and DH-7 and DH-8 in [`REQUIREMENTS.md`](REQUIREMENTS.md).
- Searching or filtering one's own past threads. SS-18 (C). Not part of this work.
- Deleting a document, and the `deleting` state. [`DOCUMENT-DELETE-REQUIREMENTS.md`](DOCUMENT-DELETE-REQUIREMENTS.md) (DD-n). This document only says how the filters treat that state.
- Source chips, stored source lists and the auth rule for endpoints that return passages. [`CITATION-RULES.md`](CITATION-RULES.md), CB-56 and CB-67.
- Recording the corpus (authority or firm procedure) at upload. UP-2. The source type filter depends on it (section 8).
- Withdraw and supersede. UP-6 and UP-5.
- Sharing threads. Off in `.chainlit/config.toml` line 48 (`allow_thread_sharing = false`). Bulk rename or delete. Not requested.

## 2. What exists today

| Component | Current state | Verified in |
|---|---|---|
| Thread routes | Router prefix `/api/chat`. `GET /api/chat/threads`, `GET /api/chat/threads/{thread_id}/messages`, `DELETE /api/chat/threads/{thread_id}`. No rename route. | `app/routes/chat_history.py` lines 12, 15, 79, 136 |
| Thread storage | Chainlit's `SQLAlchemyDataLayer` on `CHAINLIT_DATABASE_URL`. Tables `threads`, `steps`, `elements` (and `feedbacks`, which Chainlit's delete also clears). None of these tables is defined in the repo; their schema exists only in the live database and was not checked. | `app/chainlit/chainlit_app.py` lines 18-22; grep of the repo for the table names |
| Ownership rule | A thread is the user's when `threads."userIdentifier"` equals the session email or `sub`. The list query applies it. The messages route checks it before reading and returns 404 otherwise. | `app/routes/chat_history.py` lines 28-29, 47-48, 93-99 |
| List | Newest 20 threads by `createdAt`. Name is `threads.name`, else the first user message, else "New Conversation", then cut to 35 characters plus "...". A database error returns an empty list. | `app/routes/chat_history.py` lines 31-51, 64-66, 74-76 |
| Automatic title | Chainlit writes the first user message of a session into `threads.name`. A resumed thread is marked as already started, so a later message does not rename it. | pinned `chainlit==2.11.1` (`requirements.txt` line 1): `chainlit/emitter.py` lines 237-255, 281-283; `chainlit/socket.py` lines 220-225 |
| Delete endpoint | Deletes the thread's `steps`, then its `elements` (an error there is swallowed), then the `threads` row where the owner matches, and returns `{"status": "ok"}`. The owner check is only on the last statement. `feedbacks` and element files are not removed. | `app/routes/chat_history.py` lines 136-165 |
| Delete control | Trash button on every sidebar row, `title="Delete conversation"`. `window.confirm('Are you sure you want to delete this conversation?')`. On success the row is removed without reload; if it was open, the page goes to `/assistant`. On failure, `alert` with fixed text. | `frontend/src/components/Sidebar.tsx` lines 25-51, 124-139 |
| Rename control | None. | `frontend/src/components/Sidebar.tsx` |
| Chainlit's own thread routes | `PUT /project/thread` (rename) and `DELETE /project/thread` (hard delete via `delete_thread`, which removes feedbacks, elements and their files, steps and the thread). Both check the author and return 401, not 404, for someone else's thread. Mounted under `/chat`. Not tested against a running app. | `chainlit/server.py` lines 1148-1170, 1225-1246; `chainlit/data/acl.py` lines 6-19; `chainlit/data/sql_alchemy.py` lines 299-319; `app/main.py` line 118 |
| Auth on `/chat` paths | The middleware treats any path containing `/chat` as public, so `/api/chat/threads/...` relies on the check inside each handler. | `app/main.py` lines 50-51 |
| Empty sidebar | "No past sessions yet", shown for no threads and for a failed load alike. | `frontend/src/components/Sidebar.tsx` lines 18-23, 86-89 |
| Documents list | `GET /api/documents` returns every row of `documents`, newest id first, in one response. No paging, no filter parameters. | `app/routes/upload.py` lines 92-99 |
| Document fields | `filename`, `source_label`, `storage_path`, `status`, `failure_reason`, `uploaded_by`, `uploaded_at`. No corpus or source type field. Upload copies the filename into `source_label`. | `app/db/models.py` lines 15-25; `app/db/schema.sql` lines 6-15; `app/routes/upload.py` line 54 |
| Status values | `pending` at upload and retry, `processing`, `ready`, `failed`. Retrieval reads only `ready`. `schema.sql` line 11 omits `processing` from its comment. The n8n workflow writes no status: its only step calls `POST /api/n8n/process-document/{id}`, which runs `process_document`. | `app/routes/upload.py` lines 56, 214; `app/services/document_service.py` lines 109, 165, 186; `app/rag/retriever.py` lines 110, 196; `n8n/Document Ingestion.json` |
| Documents page | One text search over `filename` and `source_label`. Status shown as the raw value in a badge (CSS has `.processed` and `.uploaded` classes, neither of which is a stored value). TYPE column shows the file extension. One "No documents found." message for both an empty list and no matches. Delete and retry act on `doc.id`. | `frontend/src/pages/Documents.tsx` lines 115-122, 182-195, 225-238, 242-244, 254-289, 299-324; `frontend/src/styles/legacy.css` lines 333, 338 |

The gap that matters most: the delete endpoint removes messages before it checks the owner. A signed-in user who sends `DELETE /api/chat/threads/{id}` for another user's thread id erases that user's messages, keeps their empty thread row, and gets `{"status": "ok"}` back. R98's first check is aimed at exactly this.

## 3. Chat rename

SS-23 (S) already asks for this. This section makes it buildable.

### 3.1 Control and interaction

| ID | P | Requirement |
|---|---|---|
| CM-1 | M | Each row in the "Recent Conversations" list has a rename control next to the delete control, with the accessible name "Rename conversation". It can be reached by mouse and by keyboard without opening the conversation. |
| CM-2 | M | Activating rename does not open the conversation. The row's title becomes a single-line text field holding the current full name, with the text selected. |
| CM-3 | M | Enter or a Save button saves. Escape or a Cancel button closes the field and keeps the previous name. Moving focus out of the field without saving also keeps the previous name. `[ASSUMED]` discard on blur, so a stray click never saves a half-typed name. |
| CM-4 | M | Only one row is in rename mode at a time. Starting rename on another row cancels the first without saving. |
| CM-5 | S | The field shows the hint "Do not include client names, TFNs or member numbers." A name is stored and listed like a message is, so DH-3 applies at this input too. |

### 3.2 Validation

The browser checks for fast feedback. The server checks again and its answer is final (CM-22).

| ID | P | Requirement |
|---|---|---|
| CM-6 | M | Before validation, leading and trailing spaces are removed and each line break or tab becomes a single space. |
| CM-7 | M | A name that is empty after CM-6 is rejected with "Name cannot be empty." Nothing is saved. |
| CM-8 | M | A name longer than 100 characters after CM-6 is rejected with "Name must be 100 characters or fewer." Nothing is saved. Pasted text is not cut silently. `[ASSUMED]` 100 characters: enough for a full question, and the sidebar shows far less. |
| CM-9 | M | Any printable characters are accepted, including punctuation, `$`, `%` and non-English letters. The name is shown as plain text: `<b>test</b>` and `**test**` display literally, never as HTML or Markdown. |
| CM-10 | M | Duplicate names are allowed. Each conversation is still identified by its id. |
| CM-11 | S | Saving a name identical to the current one closes the field and sends no request. |
| CM-12 | M | While the name is invalid, Save is disabled and the message shows under the field. The field stays open with the typed text so it can be corrected. |

### 3.3 Persistence and the automatic title

| ID | P | Requirement |
|---|---|---|
| CM-13 | M | A saved name is stored in `threads.name` and shows in the sidebar at once, without a page reload. |
| CM-14 | M | After a refresh, after signing out and in, and on another device, the list shows the saved name. |
| CM-15 | M | `GET /api/chat/threads` returns the full stored name. The sidebar shortens it for display (it already applies an ellipsis in inline styles, `Sidebar.tsx` lines 108-121) and shows the full name on hover and in the rename field. Today the endpoint cuts names to 35 characters (lines 64-66), so the field would open with a cut name. |
| CM-16 | M | A conversation that has never been renamed keeps today's automatic title (section 2, "List" and "Automatic title"). |
| CM-17 | M | Once a user renames a conversation, nothing replaces that name automatically: not reopening it, not sending more messages in it, not a reconnect. If a resume fails, Chainlit treats the next message as the first one and writes it into `threads.name` (`chainlit/emitter.py` lines 281-283), so this needs its own test. |
| CM-18 | M | Renaming changes only the name. Messages, ownership and `createdAt` are unchanged, so the conversation keeps its place in the list (ordered by `createdAt`, line 49). |
| CM-19 | S | If one conversation is renamed in two tabs, the last save wins. The other tab shows the stored name after its next refresh. No live sync, consistent with SS-34. |

### 3.4 Rename endpoint

| ID | P | Requirement |
|---|---|---|
| CM-20 | M | Rename is a server endpoint that reads the signed-in user from the session inside its own handler and returns 401 without one. `[ASSUMED]` `PATCH /api/threads/{thread_id}` with body `{"name": "..."}`. The path has no `/chat` because `app/main.py` lines 50-51 let any path containing `/chat` skip the middleware auth guard. Outside `/chat`, this write route gets AU-85 as a second layer on top of the ownership check in CM-21. |
| CM-21 | M | The endpoint updates the row only where the id matches and the owner is the signed-in user, by the same rule as the messages route (lines 93-99). A thread that does not exist or belongs to someone else returns 404 and is unchanged (SS-36). |
| CM-22 | M | The endpoint applies CM-6 to CM-8 itself and returns 422 with the same messages for an invalid name, whatever the browser sent. |
| CM-23 | M | The sidebar does not call Chainlit's `PUT /chat/project/thread`, and that route is blocked or made to follow CM-21 and CM-22, as CM-33 does for delete. A signed-in user can call it directly: it skips CM-22, including the 100-character limit, and it returns 401 for another user's thread, which confirms the thread exists (contrary to SS-36). |
| CM-24 | M | If saving fails, the field stays open with the typed text and shows "The name could not be saved. Try again." Raw error text is not shown. On 404 the message is "This conversation no longer exists." and the row is removed. |

## 4. Chat delete

### 4.1 Conflict with retention, stated and resolved

[`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md) SS-17 (M) says a user cannot delete their own history unilaterally. SS-44 (M) says no deletion mechanism is added before the client sets a retention period (DH-8). DH-7 asks the firm to be able to show what the tool said, and AU-61 keeps history even when an account is disabled. Cards R130 and R103 ask for delete "including its messages", and the code already erases them (section 2).

Resolution, `[ASSUMED]` until the client answers open question 1: the user's delete is final from the user's side and keeps the records for the firm. The conversation leaves the user's list and cannot be opened again by them, and its rows stay in the database. SS-17, SS-44 and DH-7 win on the stored data, because a sidebar card cannot decide a retention rule the client has not set, and an erased thread cannot be recovered if the answer turns out to be "keep". The cards win on what the user sees. A hide marker removes nothing, so it is not the deletion mechanism SS-44 rules out. If the client allows users to erase their own history, CM-32 becomes what the action does, and the only UI change is the sentence in CM-27.

### 4.2 Control and confirmation

| ID | P | Requirement |
|---|---|---|
| CM-25 | M | The existing delete control stays on each row, with the accessible name "Delete conversation". Activating it does not open the conversation. |
| CM-26 | M | Delete needs confirmation in an in-app dialog, as DD-11 requires for documents. `window.confirm` (Sidebar line 28) is replaced. No request is sent until the user confirms. |
| CM-27 | M | The dialog names the conversation, says it will be removed from the user's list and cannot be opened again, and, while CM-29 applies, says a record is kept. It never says the conversation is permanently erased while it is not, the same honesty rule SS-20 sets for new-chat copy. `[ASSUMED]` wording: title "Delete this conversation?"; body "'{name}' will be removed from your conversations and you will not be able to open it again. Alfa Focus keeps a record of it." |
| CM-28 | M | Cancel, Escape and closing the dialog send no request and change nothing. Cancel has initial focus. The confirm button reads "Delete conversation", not "OK" or "Yes" (as DD-15). |

### 4.3 What delete removes

| ID | P | Requirement |
|---|---|---|
| CM-29 | M | `[ASSUMED]` Interim rule (section 4.1): a confirmed delete marks the thread as deleted by its owner and records the time. Its steps, elements, feedback and any stored source list (CB-56) are kept unchanged. Where the marker lives is a build choice: Chainlit's `threads.metadata`, which its data layer already reads, if that column exists in the live schema (unverified, section 2), or a new column. |
| CM-30 | M | A thread marked deleted is absent from `GET /api/chat/threads`; its messages route returns 404; rename returns 404; and opening `/assistant?threadId={id}` shows that the conversation does not exist and does not resume it. This holds after refresh and on any device. The REST routes are not enough: `@cl.on_chat_resume` (`app/chainlit/chainlit_app.py` lines 86-105) rebuilds history from the Chainlit thread over the socket without calling them, so the resume path must refuse a hidden thread too. |
| CM-31 | M | Nothing else changes: the user's other threads, other users' threads, `documents`, `document_chunks`, `eval_results` and `app_users`. |
| CM-32 | M | A permanent delete, once allowed (open question 1), removes in one database transaction: the `threads` row; every `steps` row with that `threadId`; every `elements` row with that `threadId` and the stored file behind each; every `feedbacks` row for those steps; and any stored source list and passage text for those turns (CB-56). If any part fails, nothing is removed. It never removes a document or its chunks, the reverse of DD-35. |
| CM-33 | M | While CM-29 applies, Chainlit's `DELETE /chat/project/thread` cannot be used to erase a thread. It is blocked, or made to follow CM-29. Otherwise any user can bypass section 4.1 for their own threads. |

### 4.4 After confirming

| ID | P | Requirement |
|---|---|---|
| CM-34 | M | While the request runs, the row's delete and rename controls are disabled. A second click sends no second request. |
| CM-35 | M | On success, the row leaves the list without a reload and the message "Conversation deleted." shows. If it was the open conversation, the page moves to a new empty chat at `/assistant`, as today (Sidebar lines 40-43). |
| CM-36 | M | On failure, the row stays, nothing has changed, and the message is "The conversation could not be deleted. Try again." Raw error text is not shown. |
| CM-37 | S | On 404 (already deleted in another tab), the message is "This conversation no longer exists." and the row is removed, as DD-42 does for documents. |
| CM-38 | S | A conversation deleted in one tab and still open in another does not return to the list when a message is sent from the stale tab. The stale tab shows that it no longer exists on its next action or refresh. |

### 4.5 Delete endpoint and ownership

| ID | P | Requirement |
|---|---|---|
| CM-39 | M | The delete endpoint reads the session in its own handler (401 without one), then confirms the thread exists and belongs to the signed-in user before it changes anything. Otherwise it returns 404 and no row in any table changes. This fixes the defect in section 2. |
| CM-40 | M | The endpoint reports success only when exactly one thread of the signed-in user was marked (CM-29) or removed (CM-32). |
| CM-41 | S | The existing paths `GET /api/chat/threads`, `GET /api/chat/threads/{thread_id}/messages` and `DELETE /api/chat/threads/{thread_id}` may stay for this work, because each checks the session in its own handler. This leaves a split surface: rename at `/api/threads`, list, messages and delete at `/api/chat/threads`. Moving the GET and DELETE routes to `/api/threads` is one decision, open question 3. |
| CM-42 | M | List, open, rename and delete act only on the signed-in user's threads. Two accounts never see or change each other's threads (SS-1, SS-36). |

## 5. Document list filters

### 5.1 Placement and controls

| ID | P | Requirement |
|---|---|---|
| DF-1 | M | Two filters, "Status" and "Source type", sit in the "Uploaded Documents" header beside the search box, above the table. They stay visible whenever the list has loaded, including when nothing matches. |
| DF-2 | M | Each filter is multi-select. With no value ticked, that filter is off. |
| DF-3 | M | Each row shows its status and its source type as text, so a tester can check every visible row against the filters. |
| DF-4 | S | Both filters are labelled and keyboard operable. The result line (DF-12) is announced to screen readers when it changes. |

### 5.2 Status values

| ID | P | Requirement |
|---|---|---|
| DF-5 | M | Status options and the stored values they match: "Pending" = `pending`, or no status (shown as pending today, `Documents.tsx` line 254); "Processing" = `processing`; "Processed" = `ready`; "Failed" = `failed`; "Deleting" = `deleting` (DD-45), which also covers rows shown as "Delete incomplete" under DD-26; "Superseded" = `superseded`; "Withdrawn" = `withdrawn`. |
| DF-6 | M | An option appears only for a status the code can produce. "Superseded" and "Withdrawn" are added when UP-5 and UP-6 create those states, and "Deleting" when DD-45 is built. `[ASSUMED]` |
| DF-7 | M | Matching ignores case. A row whose status is not listed in DF-5 shows when the status filter is off, and matches an "Other" option that appears only while such a row exists. No row is dropped silently. |

### 5.3 Source type values

| ID | P | Requirement |
|---|---|---|
| DF-8 | M | Source type options: "Official source" (corpus recorded as authority), "Internal procedure" (corpus recorded as firm procedure), and "Type not recorded" (no corpus recorded). These are the labels in CB-31. |
| DF-9 | M | Source type comes from the document's recorded corpus (the `corpus` field in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 5.1, captured under UP-2). It is never inferred from `filename` or `source_label`. |
| DF-10 | M | Until the corpus is recorded, every document matches "Type not recorded" only. The filter is still built and tested against that value. |

### 5.4 Combining and clearing

| ID | P | Requirement |
|---|---|---|
| DF-11 | M | Ticked values within one filter combine with OR. The two filters and the search text combine with AND. Example: Status "Failed" and "Pending", with Source type "Official source", shows official documents that are failed or pending. |
| DF-12 | M | While any filter or search text is active, a line above the table reads "Showing X of Y documents", where Y is the full loaded list. |
| DF-13 | S | Each option shows how many documents in the full loaded list have that value, for example "Failed (3)". Counts ignore the other filter and the search. `[ASSUMED]`: counts stay stable while the user ticks values. |
| DF-14 | M | A "Clear filters" control shows while any filter or search text is active. It unticks every value, empties the search box and shows the full list. Each value can also be unticked on its own. |
| DF-15 | M | A change to a filter updates the table at once, with no Apply button and no page reload. |

### 5.5 Persistence after refresh

| ID | P | Requirement |
|---|---|---|
| DF-16 | M | Active filters are held in the page URL query string as `status` and `type`, comma-separated, for example `/documents?status=failed,pending&type=official`. `[ASSUMED]` names and values: `status` uses the stored values; `type` uses `official`, `internal` and `none`. |
| DF-17 | M | After a refresh, or Back and Forward, the same values are ticked and applied. The URL opened by another signed-in user shows the same filtered view. |
| DF-18 | M | Filters are not saved on the server or in browser storage. Opening Documents from the sidebar starts with no filters. |
| DF-19 | S | Unknown values in the query string are ignored, the valid ones are applied, and the URL is rewritten without the unknown ones. |
| DF-20 | C | The search text is held in the URL as `q`, so it also survives a refresh. |

### 5.6 Client-side filtering

| ID | P | Requirement |
|---|---|---|
| DF-21 | M | Filtering runs in the browser on the list already loaded from `GET /api/documents`. That endpoint returns every document in one response, and the full corpus is 73 documents (`corpus/manifest.json`; `docs/corpus_check_report.md` on `main` reports 42 loaded so far), so no new endpoint is needed and a change applies without a round trip. |
| DF-22 | S | If `GET /api/documents` gains paging, or the list passes `[ASSUMED]` 500 documents, filtering moves to the server with the parameter names in DF-16, so saved URLs keep working. Filtering one page in the browser would hide matches on other pages. |

### 5.7 Delete, retry and upload while filtered

| ID | P | Requirement |
|---|---|---|
| DF-23 | M | Delete and retry act on the row's document id, never on its position in the filtered list. Filters never change which actions a row offers; DD-4, DD-6 and DD-30 decide that. |
| DF-24 | M | When a document is deleted while filters are set (DD-39), the filters stay set, the row leaves the list, and the counts and DF-12 line update. If no row is left, DF-27 shows. |
| DF-25 | M | After a retry the list reloads (`Documents.tsx` line 106) with the filters still set. If the document's new status no longer matches, it leaves the view and the message "Processing restarted for {filename}." confirms the action. |
| DF-26 | S | After an upload the filters stay set. If the new document is hidden by them, the message reads "{filename} uploaded. It is hidden by the current filters." |

## 6. Empty and error states

| ID | P | Situation | Required behaviour |
|---|---|---|---|
| DF-27 | M | Documents exist but none match the filters and search | The table body says "No documents match these filters." with a "Clear filters" button. The filters stay visible with their values ticked. |
| DF-28 | M | No documents exist | The table body says "No documents uploaded yet." It never shows the DF-27 text. |
| DF-29 | M | The list failed to load | The existing load-failure message shows (`Documents.tsx` lines 210-223). Neither DF-27 nor DF-28 shows, and the filters are not applied to a list that did not load. |
| CM-43 | M | The user has no conversations, including after deleting the last one | The sidebar shows its existing "No past sessions yet". |
| CM-44 | M | The conversation list failed to load | The sidebar says "Your past conversations could not be loaded." and not the CM-43 text (SS-31). Today a database error returns an empty list (lines 74-76), so a failure reads as "no history". |

## 7. Conflicts and dependencies

| Existing source | This document | Resolution |
|---|---|---|
| SS-17, SS-44 (M); DH-7; AU-61 | R103 asks for delete including messages; the code erases them | Section 4.1: hide and keep records until the client answers. SS-17 and SS-44 win on stored data. |
| SS-23 (S), rename | CM-1 to CM-24 | Implements SS-23. No conflict. |
| `docs/DATABASE.md` line 39: `source_label` is `"law"` or `"firm"` | DF-9 | The code writes the filename there (`upload.py` line 54), so DATABASE.md is out of date. The filter does not read `source_label`. Correcting DATABASE.md is a separate change. |
| R104 card: "processed, processing, failed, superseded" | DF-5, DF-6 | "Processed" is the label for the stored value `ready`. "Pending" is added because the state exists. "Superseded" waits for UP-5. |
| `app/main.py` lines 50-51: any path containing `/chat` skips the auth guard (AU-85); CB-67 applies this to passage endpoints only | CM-20, CM-41 | The new rename route sits outside `/chat` for the same reason, so it gets the guard as well as its own check. The existing routes keep their in-handler checks. |
| Chainlit's own rename and delete routes | CM-23, CM-33 | Not used by the sidebar. Both are blocked, or made to follow this document, while CM-29 applies. |
| UP-2 and the `corpus` field in REQUIREMENTS.md section 5.1 | DF-8 to DF-10 | Not in `models.py` or `schema.sql`. Needs a column, capture at upload and a back-fill. R128 describes the 73 corpus documents as official sources, so `[ASSUMED]` they back-fill as "Official source". R129 already expects "source type" to be stored. No Sprint 3 card owns the column (open question 4). |

## 8. Current build against these requirements

For R103 and R104 (what to change) and R98 (what fails on today's main).

| IDs | Today | Change needed |
|---|---|---|
| CM-1 to CM-14, CM-19 to CM-24 | Not met. No rename control or route. | Build. |
| CM-15 | Not met. Names cut to 35 characters. | Return the full name. |
| CM-16 | Met. | Keep. |
| CM-17, CM-18 | Not testable until rename exists. | Test after reopening a thread. |
| CM-25 | Partly met. Button with `title` only. | Accessible name. |
| CM-26 to CM-28 | Partly met. `window.confirm` with generic text. | In-app dialog. |
| CM-29 to CM-31 | Not met. Delete erases steps and elements. | Hide marker; filter it from list, messages and resume. |
| CM-32 | Not met even as an erase: feedbacks and element files stay. If the `elements` delete fails, Postgres aborts the transaction, so swallowing that error does not let the rest succeed (expected Postgres behaviour, not tested). | Only when open question 1 allows it. |
| CM-33 | Not met. Chainlit route available. | Block or redirect it, with the rename route (CM-23). |
| CM-34, CM-37, CM-38 | Not met. | Build. |
| CM-35, CM-36 | Partly met. Row removed and redirect work; no message. | Messages. |
| CM-39, CM-40 | Not met. Messages removed before the owner check; always `ok`. | Check owner first; 404 otherwise. |
| CM-42 | Met for list and messages, not for delete. | CM-39. |
| CM-43 | Met. | Keep. |
| CM-44 | Not met. | Distinguish failure from empty. |
| DF-1 to DF-22, DF-24 to DF-28 | Not met. Only a text search exists. | Build. |
| DF-3 | Partly met. Status shown; source type not. | Add source type. |
| DF-23, DF-29 | Met. | Keep. |

## 9. Test mapping for R98

Use two `staff` accounts, A and B, and run the chat checks with both. Manan tests, not Zekun, because Zekun builds R103 and R104.

| R98 check | How | Requirements |
|---|---|---|
| A user cannot see or delete another user's chats | A creates a thread and notes its id from the URL. As B: A's thread is not listed; its messages route, rename route and delete route each return 404; Chainlit's `PUT` and `DELETE /chat/project/thread` for it are refused. As A: the thread, its name and every message are intact. | CM-21, CM-23, CM-33, CM-39, CM-40, CM-42 |
| Deleting a chat asks for confirmation and removes it after refresh | Cancel, Escape and close leave it. Confirm removes it. After refresh it is still gone, and its URL shows it does not exist. Delete the open thread: the page moves to a new chat. With database access, its rows still exist (CM-29). | CM-26 to CM-30, CM-35 |
| A deleted chat cannot be resumed | Delete a thread, then open `/assistant?threadId={id}` directly and in a second tab where it was open. No history loads over the socket (`on_chat_resume` does not run for it), a message sent there does not attach to it, and it does not return to the list. | CM-30, CM-38 |
| Rename (card description) | Rename and refresh; empty and spaces only; 101 characters; a pasted multi-line name; `<b>test</b>`; a duplicate name; Escape; reopen the thread, send a message, refresh. | CM-6 to CM-18 |
| Each filter and the combination returns only matching documents | Each status value alone; each source type alone; both together; both with search text. Every visible row must match. Record "Official source" and "Internal procedure" as blocked until the corpus is recorded (DF-10), and "Superseded" and "Withdrawn" as not applicable (DF-6). | DF-5 to DF-11 |
| Clearing filters restores the full list and empty results show the empty state | Clear filters gives Y of Y. A combination with no match shows DF-27; the list failing to load shows DF-29, not DF-27. | DF-12, DF-14, DF-27 to DF-29 |
| Filters persist and do not break actions | Refresh with filters set; Back and Forward; delete and retry a row while filtered. | DF-16, DF-17, DF-23 to DF-25 |
| Defects recorded with reproduction steps | Log each failure against the ID it breaks. | All |

## 10. Open questions

| # | Question | Who | Affects |
|---|---|---|---|
| 1 | May a user erase their own conversation, or only remove it from their list? If only remove, may an administrator erase one later? Same as question 2 in [`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md) section 10 and question 6 in `REQUIREMENTS.md`. | Client | CM-27, CM-29, CM-32, CM-33 |
| 2 | If a user types a client identifier into a chat by mistake, against DH-3, who removes it, and what is the target time from report to removal? | Client | CM-32 |
| 3 | Should `GET /api/chat/threads`, `GET /api/chat/threads/{id}/messages` and `DELETE /api/chat/threads/{id}` move to `/api/threads` with rename, as one change, so the whole thread API sits under the auth guard? | Team | CM-20, CM-41 |
| 4 | Who adds the `corpus` field, captures it at upload (UP-2) and back-fills the loaded documents? | Team | DF-8 to DF-10 |
| 5 | Are the 100-character limit and discard-on-blur acceptable? | Team, with R136 | CM-3, CM-8 |

## 11. Handoff to UX, Dev and Test

- **R136, Manan Chaudhary (wireframes):** rename states (view, editing, each invalid message, saving, failed) from CM-1 to CM-12 and CM-24; the delete dialog in CM-26 to CM-28; in-progress, success, failure and 404 states in CM-34 to CM-37; both filters with counts and the result line (DF-1, DF-2, DF-12 to DF-14); source type on each row (DF-3); the empty states in section 6. Keep the delete dialog consistent with the document delete dialog in R120 (DD-11 to DD-15).
- **R103, Zekun Liu (chat build):** fix CM-39 first, before any UI work. Then the rename route (CM-20 to CM-22), the full name in the list (CM-15), the hide marker (CM-29 to CM-31), including a check in `@cl.on_chat_resume` so a hidden thread cannot resume (CM-30), and blocking Chainlit's rename and delete routes (CM-23, CM-33).
- **R104, Zekun Liu (filter build):** DF-1 to DF-29, in the browser, with URL state. Build source type against "Type not recorded" (DF-10) and agree the corpus field with whoever takes open question 4. R128 and R129 are also Zekun's, so the back-fill can follow the bulk load.
- **R98, Manan Chaudhary (test):** section 9.
- **Hayden Nguyen (PM):** confirm the interim rule in section 4.1 and answer open questions 3 and 4. Questions 1 and 2 go to the client meeting with [`CLIENT-MEETING-QUESTIONS.md`](CLIENT-MEETING-QUESTIONS.md).

Nothing in sections 3 to 6 is verified against a running system. Section 2 and section 8 are a code reading of main at `e1ec4b0` and of the pinned Chainlit package, not test results.
