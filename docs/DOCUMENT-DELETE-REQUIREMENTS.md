# Document delete requirements

Team 83, Alfa Focus Knowledge Assistant.
Drafted 2026-10-07 by Ronith Mugundakumar.
Surfaces: the delete action on the Documents page (`frontend/src/pages/Documents.tsx`), the `DELETE /api/documents/{document_id}` endpoint (`app/routes/upload.py`), and everything that endpoint touches: Supabase Storage, the `documents` and `document_chunks` tables, retrieval, and chat history.

Defines who may delete a document, which documents can be deleted, the confirmation step, exactly what is removed and what is kept, the order of operations, what happens when a step fails part-way, how superseded versions are handled, what happens to past answers that cited the deleted document, and what the user sees afterwards. Requirement IDs are `DD-n` and are stable, per the traceability rule in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10.

**Status: partially implemented and demoed.** Delete works end to end for the roles `admin` and `staff` (the server returns 403 to `team`), with an in-app confirmation dialog naming the file and a success or error message. Not built: the `deleting` marker state and ordered, recoverable steps (section 8), the `processing` refusal, stale limits, plain-text errors, hiding the control by role, deletion records, and everything about superseded versions. The role differs from DD-1 (`admin` only): the code allows `admin` and `staff`. Section 2 records what the code does and section 13 maps it against each requirement. Requirements marked `[ASSUMED]` need client or team confirmation before they drive a sprint. The largest is the role: AU-9 gives withdrawal to `admin`, and AU-9 is itself `[ASSUMED]`.

Priorities are MoSCoW: **M** must, **S** should, **C** could.

## 1. Purpose and scope

Delete is the one action on the Documents page that cannot be undone, and it reaches three places at once: a file in Supabase Storage, a row in `documents`, and the chunks and embeddings in `document_chunks` that retrieval reads. Storage and Postgres do not share a transaction, so "delete a document" is several steps that can fail independently. This document fixes what a complete delete is, what a failed one must leave behind, and who may start one.

**In scope:** a single admin deleting a single document from the Documents page, the endpoint behind it, its effect on retrieval, superseded versions and chat history, and the record kept of the deletion.

**Out of scope**, with the document that owns each:

- Withdrawing a document from search while keeping it (UP-6, and the `withdrawn` state in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 5.1). Section 3 states how delete and withdraw differ; building withdraw is not part of this work.
- Uploading a new version and marking the old one superseded (UP-5). Section 9 covers only what delete does to versions that already exist.
- Retry and stuck-job recovery for failed or pending ingestion. That is I-3 in `docs/ITERATION-AND-EXPLORATION.md` (a file that is not on `main`); a retry endpoint exists but no stuck-job recovery.
- Deleting chat threads (`DELETE /api/chat/threads/{thread_id}` in `app/routes/chat_history.py`, built). That is governed by SS-17 in [`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md).
- Bulk delete and account deletion. Not requested.

## 2. What exists today

| Component | Current state | Verified in |
|---|---|---|
| Delete endpoint | `DELETE /api/documents/{document_id}`, guarded by `require_document_delete_permission`. Selects `id, storage_path` for the id, returns 404 if absent, removes the file from the bucket, then deletes the `documents` row. Returns 404 "Document could not be deleted" if the row delete returns no data, and 500 with `str(e)` on any other exception. | `app/routes/upload.py` (`delete_document`) |
| Order and atomicity | Storage file first, database row second, as two separate calls through the Supabase client. Not atomic. The return value of `storage.from_(bucket).remove([storage_path])` is not checked. | `app/routes/upload.py` (`delete_document`) |
| Chunks and embeddings | Not deleted by the endpoint. Removal depends on the foreign key `document_chunks.document_id references documents(id) on delete cascade` in `schema.sql`. Embeddings are a column on `document_chunks`, so there is no separate vector store to clean. `models.py` declares the same foreign key without `ondelete`. Its `cascade="all, delete-orphan"` on the relationship applies only to deletes made through a SQLAlchemy session, not to the Supabase client call the endpoint uses. Whether the live Supabase tables carry the cascade was not checked (no database access for this task). | `app/db/schema.sql` lines 17-24, `app/db/models.py` lines 27, 35 |
| Role check | Built, server side. `require_document_delete_permission` (in `app/auth/deps.py`) loads the user from the session and allows roles `admin` and `staff`; any other role (`team`) gets 403 "You do not have permission to delete documents." No session gets 401. | `app/auth/deps.py`; `app/routes/upload.py` |
| Delete control | A trash button on every row, for every status, shown to every signed-in user regardless of role (no role check in `Documents.tsx`); it is disabled while a delete is running. `/documents` is wrapped in `RequireAuth` only. A `team` user sees the button and gets a 403 message on click. | `frontend/src/pages/Documents.tsx`; `frontend/src/App.tsx` |
| Confirmation | In-app modal dialog (`role="dialog"`): "Delete document?", names the filename, says the stored file and indexed content will be removed and that this cannot be undone, with Cancel and "Confirm delete". Clicking the backdrop or Cancel sends no request. It does not show the source label, mention past answers (DD-13), or set initial focus on Cancel. | `frontend/src/pages/Documents.tsx` |
| After success | The row is removed from local state without a reload and a status message shows the server's "Document deleted" text. | `frontend/src/pages/Documents.tsx` |
| After failure | An inline `role="alert"` error message shows the server's `detail`, which can be raw exception text (`str(e)`) on a 500. While a delete runs the dialog buttons and every trash button are disabled and the confirm button reads "Deleting...". | `frontend/src/pages/Documents.tsx`; `app/routes/upload.py` |
| Status values | `pending`, `processing`, `ready`, `failed`. Retrieval reads only `ready` documents. | `app/db/models.py`, `app/rag/retriever.py` |
| Ingestion during delete | n8n calls `POST /api/n8n/process-document/{id}`, which runs `process_document`. A missing document raises `ValueError` and returns 404. Chunks are inserted and committed in one block after old chunks are removed. | `n8n/Document Ingestion.json`, `app/routes/integration.py`, `app/services/document_service.py` |
| Retry endpoint | `POST /api/documents/{id}/retry` refuses only `ready`; any other status is reset to `pending` and re-triggered. Neither it nor upload has a role check. | `app/routes/upload.py` |
| Versions and supersession | Not modelled. No `version` or `superseded_by` column. The design in `docs/RAG-DESIGN.md` section 4 proposes `superseded_by` and says refresh must "never delete". | `app/db/models.py`, `app/db/schema.sql`, `docs/RAG-DESIGN.md` |
| Chat history | Thread steps are stored in the Chainlit tables (`threads`, `steps`); the stream endpoint inserts them directly. The assistant step holds the answer text only. The sources sent to the page are not saved with the turn. | `app/routes/chat_history.py`, `app/chainlit/chainlit_app.py`, `app/rag/retriever.py` |
| Uploader identity | `uploaded_by` is written as the literal `"user"`, so "the uploader may delete their own document" cannot be implemented today. | `app/routes/upload.py` |
| Deletion record | None. Nothing records who deleted what, or when. | `app/db/schema.sql` |

The gap that matters most: if the row delete fails after the file has been removed, the row keeps its `ready` status and its chunks, so retrieval keeps citing a document whose file no longer exists, and the retry button would re-ingest from a missing file.

## 3. Delete, withdraw and supersede

Three different actions take a document out of current answers. They must not be built as one.

- **Delete** (this document) removes the file, the record, and the chunks. It is for a document that should never have been in the knowledge base: the wrong file, a duplicate, a test upload, or a failed upload nobody will retry.
- **Withdraw** (UP-6) keeps everything and excludes the document from retrieval. It is the right action for a valid document the firm no longer wants answered from.
- **Supersede** (UP-5) keeps the old version for past-year questions and points it at the new one.

**Conflict, stated.** UP-5 and `docs/RAG-DESIGN.md` section 4 say an old version is superseded "rather than deleting it" and that refresh must "never delete". DH-7 requires the firm to show what the tool said. A hard delete removes the passages an earlier answer was based on. Resolution: delete stands as a manual admin action because the card requires it and a knowledge base with no way to remove a wrong file is worse. UP-5 and the RAG-DESIGN rule still win for versioning: uploading a new version never deletes the old one, and no automated process ever calls delete. DD-43 keeps a record of each deletion so DH-7 can still say which document an answer cited. Whether that is enough for the firm's obligations is open question 1.

## 4. Who can delete

| ID | P | Requirement |
|---|---|---|
| DD-1 | M | Only accounts with role `admin` can delete a document. `staff` and `team` cannot. `[ASSUMED]` from AU-9 ("admin may additionally upload, withdraw documents"). |
| DD-2 | M | The role check runs on the server for every delete request, using the role from the server's session record per AU-40. A request from a non-admin returns 403 and changes nothing: the file, the row and the chunks are all still present afterwards. |
| DD-3 | M | An unauthenticated delete request returns 401 and changes nothing. This already holds through the middleware (AU-85) and must keep holding. |
| DD-4 | S | Users who cannot delete do not see the delete control at all, rather than a disabled one. |

## 5. Which documents can be deleted

| ID | P | Requirement |
|---|---|---|
| DD-5 | M | A document in `ready`, `failed` or `pending` can be deleted. A document in `deleting` can be deleted again only as a retry under DD-9. |
| DD-6 | M | A document in `processing` cannot be deleted. The server returns 409 with a message that the document is still being processed, and nothing changes. |
| DD-7 | S | A document that has been in `processing` for longer than a stale limit is treated as stuck and can be deleted. `[ASSUMED]` limit of 15 minutes, by analogy with the 15 minutes I-3 gives as its example for `pending` documents. Needs a recorded processing start time (section 12). |
| DD-8 | M | The status check in DD-5 to DD-7 is made on the server at the moment of deletion, inside the same locked read that starts the delete, not from the status the page showed when the dialog opened. |
| DD-9 | M | A delete is in flight while the row has been in `deleting` for less than a stale limit, `[ASSUMED]` 2 minutes. A second delete request for an in-flight document returns 409 and does not start a second delete. Once the limit has passed, the row counts as "Delete incomplete" (DD-26) and a new delete request is accepted as a retry. The time the row entered `deleting` is recorded so this can be tested. |
| DD-10 | M | After a delete completes, no `document_chunks` row exists for that document id, including when an ingestion run for it was triggered before or during the delete. An ingestion run for a deleted id ends without creating any row. |

## 6. Confirmation step

| ID | P | Requirement |
|---|---|---|
| DD-11 | M | Delete needs an explicit confirmation in an in-app dialog. No request is sent to the server until the user confirms. |
| DD-12 | M | The dialog shows the document's filename and source label, and states that the stored file, the document record, and all of its searchable passages will be removed, that it will no longer be used in answers, and that this cannot be undone. |
| DD-13 | M | The dialog states that past answers which cited this document stay in chat history as they were given (DD-35). |
| DD-14 | M | Cancel, Escape, and closing the dialog all send no request and leave the document unchanged. Cancel has the initial focus. |
| DD-15 | S | The confirm button is labelled "Delete document", not "OK" or "Yes". |
| DD-16 | S | Where the document supersedes or is superseded by another, the dialog says so and names the other version (section 9). |

## 7. What is removed and what is kept

| ID | P | Requirement |
|---|---|---|
| DD-17 | M | The file at the document's `storage_path` in the configured bucket (`SUPABASE_BUCKET`, default `documents`) is removed. |
| DD-18 | M | The document's row in `documents` is removed. |
| DD-19 | M | Every row in `document_chunks` with that `document_id` is removed, which removes its content and embedding. The delete removes them explicitly in the same transaction as DD-18, or relies on a cascade that has been confirmed to exist in each live database. It does not assume the cascade from `schema.sql`. |
| DD-20 | M | After a delete, the document is absent from `GET /api/documents`, `GET /api/documents/{id}/status` returns 404, and neither dense nor keyword retrieval returns any chunk with that document id. |
| DD-21 | M | Nothing else is removed or changed: other documents (including one with the same filename), chat threads and steps, `eval_results`, and `app_users` are untouched. |
| DD-22 | M | Delete selects its target by document id only, never by filename or storage path pattern. |

## 8. Order of operations and failure behaviour

Storage and Postgres cannot be committed together, so the delete runs in a fixed order with a marker state that keeps a half-finished delete out of search and visible on the page.

The row lock in step 1 and the single transaction in step 3 are not available through the Supabase PostgREST client the endpoint uses today (`delete_document` in `app/routes/upload.py`). The database steps must move to a SQLAlchemy session from `app/db/database.py`, as `process_document` already uses, or to a Postgres function called over RPC.

1. Lock the row, check role (DD-2) and status (DD-5 to DD-9), remember the current status, set status to `deleting`, commit. Retrieval reads only `ready`, so the document leaves search here.
2. Remove the file from Storage.
3. In one database transaction: remove the chunks, clear any supersession links (section 9), remove the row, write the deletion record (DD-43). Commit.

| ID | P | Requirement |
|---|---|---|
| DD-23 | M | Delete runs in the order above. The file is removed before the row, so at any point a row may exist without its file but a file never exists without its row. A row whose file has been removed is never `ready`. |
| DD-24 | M | If step 1 fails, nothing has changed and the user is told the delete did not start. |
| DD-25 | M | If step 2 fails, the status is set back to the value remembered in step 1. File, row and chunks are unchanged, and the user is told nothing was deleted and to try again. |
| DD-26 | M | If step 3 fails, the transaction rolls back and the row stays in `deleting`: out of search, shown on the Documents page as "Delete incomplete" with a retry-delete action. Repeating the delete completes it. |
| DD-27 | M | Delete is safe to repeat. A Storage removal for a file that is already absent counts as success at step 2, so a retry after DD-26 does not fail on the missing file. |
| DD-28 | M | Each step's result is checked. A Storage response that reports the file was not removed is a failure at step 2, not a success. |
| DD-29 | M | Error messages shown to the user are plain text that says what happened and what to do. Raw exception text is not shown. The full error is logged on the server with the document id and the step that failed. |
| DD-30 | M | The retry-processing endpoint refuses a document in `deleting`, so a half-deleted document cannot be re-ingested from a missing file. |

`deleting` is a new state. It extends the state table in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 5.1 and does not conflict with it: like `failed`, it is excluded from retrieval (DI-9).

## 9. Superseded versions

Supersession does not exist in the code today (section 2). These requirements apply once UP-5 adds a `superseded_by` link. Until then R142 records them as not applicable.

| ID | P | Requirement |
|---|---|---|
| DD-31 | M | Deleting an older version (one with `superseded_by` set) removes only that version. The newer version is unchanged. The dialog warns that questions about the period the older version covered can no longer be answered from it, which is the reason UP-5 keeps old versions. |
| DD-32 | M | Deleting a newer version that supersedes an older one clears the older version's `superseded_by` in the same transaction as step 3. `[ASSUMED]` The older version then returns to `ready` and is current again, and the dialog names it and says so. See open question 3. |
| DD-33 | M | No delete leaves a `superseded_by` value pointing at a document id that no longer exists. |
| DD-34 | S | In a chain where A is superseded by B and B by C, deleting B points A's `superseded_by` at C. C is unchanged. |

## 10. Chat history and citations

Past answers are evidence of what the tool said (DH-7). Deleting a source must not rewrite or remove them. This follows SS-35 and SS-41 in [`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md), which already require a retained turn to show the citation as given, not re-resolved against the current corpus.

| ID | P | Requirement |
|---|---|---|
| DD-35 | M | Deleting a document does not modify or delete any thread, step or turn. A thread whose answer cited the document reopens with the answer and its citation text exactly as first shown. |
| DD-36 | M | Where a citation in a retained answer offers a control that opens the source, and that source has been deleted, the control shows "This document was deleted on YYYY-MM-DD" instead of a broken link, an error, or a different document. If no deletion record exists for it (DD-43), the control shows "This document is no longer available" instead. |
| DD-37 | M | When turns store structured sources (SS-40), the stored source is not a foreign key with `on delete cascade` to `documents`, and it keeps the source label and filename as text, so deleting a document cannot delete or blank any part of chat history. |

Today DD-35 holds by default, because nothing structured links a saved answer to a document. DD-36 and DD-37 become testable when SS-40 and the source-link work (I-4, finding F13 in `docs/ITERATION-AND-EXPLORATION.md`, which is not on `main`; the chat page now shows citation chips but no viewer, see `CITATION-RULES.md`) are built.

## 11. What the user sees

| ID | P | Requirement |
|---|---|---|
| DD-38 | M | While a delete is running, the row shows an in-progress state and its delete and retry controls are disabled. A second click sends no second request. |
| DD-39 | M | On success, the row is removed from the list without a page reload, and a message names the deleted document. |
| DD-40 | M | On failure, the row stays and the message matches the failure: DD-24 and DD-25 say nothing was deleted; DD-26 says the delete is incomplete and offers retry. |
| DD-41 | M | A non-admin who sends a delete request anyway (DD-2) sees a message that they do not have permission, and the row stays. |
| DD-42 | S | If the document was already deleted by someone else (404), the message says so and the row is removed from the list. |

## 12. Deletion record and data model

Stated as requirements, not schema. `app/db/models.py` and `app/db/schema.sql` change together, as both files say.

| ID | P | Requirement |
|---|---|---|
| DD-43 | S | Each completed delete writes one record holding: document id, filename, source label, storage path, status before delete, number of chunks removed, the deleting account's `app_users.id`, and the time. `[ASSUMED]` The document's text is not kept. |
| DD-44 | S | The deletion record has no foreign key with cascade to `documents`, so it survives the delete it describes. |
| DD-45 | M | The `status` values accepted by the code include `deleting` (DD-23). |
| DD-46 | S | The time a document entered `processing` is recorded, so DD-7 can be tested. |
| DD-47 | C | An admin can see a list of deleted documents from the deletion records. |

No retention period is set for deletion records. Like SS-44, that waits for the DH-8 answer.

## 13. Current build against these requirements

For the next team (what to change, and what to expect to fail). This table reflects `main` as of 2026-10-22; card numbers elsewhere in this document (R120, R138, R142) are historical planning labels.

| ID | Today | Change needed |
|---|---|---|
| DD-1, DD-2 | Partly met. Server-side role check exists and returns 403 to `team`, but it admits `staff` as well as `admin`. | Decide whether `staff` should delete (open question 2); change `allowed_roles` if not. |
| DD-3 | Met through middleware. | Keep. |
| DD-4 | Not met. Button shown to all roles. | Hide by role. |
| DD-5 to DD-9 | Not met. Any status can be deleted; no lock; no 409. | Status rules and row lock. |
| DD-10 | Depends on the live FK. With the cascade, `process_document` fails its chunk insert for a deleted id. Not verified. | Confirm FK in each database; add a test. |
| DD-11 | Met. In-app dialog; no request until confirmed. | Keep. |
| DD-12, DD-13, DD-15, DD-16 | DD-12 partly met (filename and removal wording, no source label). DD-13 and DD-16 not met. DD-15 not met (button reads "Confirm delete"). | Dialog content. |
| DD-14 | Partly met. Cancel and backdrop click send no request; Escape handling and initial focus on Cancel are not implemented. | Add Escape and focus. |
| DD-17, DD-18 | Met on the success path. | Keep. |
| DD-19 | Relies on an unverified cascade. | Explicit chunk delete or confirmed cascade. |
| DD-20 to DD-22 | Expected to be met on the success path; not tested. | R142 test. |
| DD-23 to DD-28 | Not met. Storage first, row second, no marker state, Storage result unchecked. | Section 8 sequence. |
| DD-29 | Not met. Raw `str(e)` reaches the inline error message. | Plain messages, server log. |
| DD-30 | Not met. Retry accepts any non-`ready` status. | Refuse `deleting`. |
| DD-31 to DD-34 | Not applicable until UP-5. | None now. |
| DD-35 | Met by default. | Keep when SS-40 is built. |
| DD-36, DD-37 | Not applicable until SS-40 and source links exist. | None now. |
| DD-38 | Mostly met. Buttons disabled and "Deleting..." shown while a delete runs. | Keep. |
| DD-39 | Mostly met. Row removed without reload and a success message shows; the message does not name the document. | Name the document. |
| DD-40 to DD-42 | DD-41 partly met (the 403 text is shown). DD-40 and DD-42 not met. | Messages per case. |
| DD-43 to DD-47 | Not met. | Data model change. |

## 14. Test mapping for R142

| R142 check | Requirements |
|---|---|
| Stored file is gone from Supabase Storage | DD-17 |
| Document record and all chunks and embeddings are gone | DD-18, DD-19, DD-20 |
| Deleted document no longer returned in retrieval | DD-20 |
| Cancel leaves the document untouched | DD-11, DD-14 |
| Role without permission cannot delete | DD-1, DD-2, DD-4, DD-41 |
| Simulated failure shows an error without partial removal (card description) | DD-25, DD-26, DD-27, DD-29 |

Run the happy path and the failure checks with an `admin` test account, and the permission check with a `staff` account (DD-1). Also worth one test each: a `processing` document is refused (DD-6), a second document with the same filename survives (DD-21), and a thread that cited the deleted document reopens unchanged (DD-35).

## 15. Open questions

| # | Question | Affects |
|---|---|---|
| 1 | Does the firm need to keep a deleted document's content to show what an earlier answer was based on, or is a record of its name and dates enough? If content is needed, withdraw (UP-6) should replace delete for anything that has been `ready`. | Section 3, DD-43 |
| 2 | Who may delete: administrators only, or also the person who uploaded the document? | DD-1, AU-9. Related to question 5 in `REQUIREMENTS.md` (who may upload), which does not cover delete. The uploader option also needs `uploaded_by` to hold a real account. |
| 3 | When the newest version of a document is deleted, should the previous version become current again, or stay superseded with no current version until a replacement is uploaded? | DD-32 |
| 4 | Should Team 83 (`team`) accounts be able to delete during development, and lose that ability at handover? | DD-1, AU-10 |

## 16. Handoff

- **R120, Manan Chaudhary (UX wireframe):** sections 6 and 11. The dialog content is DD-12, DD-13 and DD-16; the states to draw are in-progress (DD-38), success (DD-39), each failure (DD-40), no permission (DD-41) and "Delete incomplete" with retry (DD-26). Show a `processing` row with delete unavailable (DD-6).
- **R138, Shihong He (build):** start from section 13. The order in section 8 and the server role check in DD-2 are the parts the current build does not have. Confirm the chunk cascade in each Supabase database before relying on it (DD-19). The lock and transaction need a SQLAlchemy session or an RPC function, not the Supabase client (section 8).
- **R142, Zekun Liu (test):** section 14. Zekun tests, not Shihong, because Shihong wrote both the current and the planned code. Mark DD-31 to DD-34, DD-36 and DD-37 not applicable and say why.
- **Client meeting:** section 15, alongside [`CLIENT-MEETING-QUESTIONS.md`](CLIENT-MEETING-QUESTIONS.md).

Nothing in sections 4 to 12 is verified against a running system. These are requirements, and section 13 is a code reading of `main` on 2026-10-22, not a test result. The delete function was demoed working on the success path.
