# Chat history and user session management requirements

Team 83, Alfa Focus Knowledge Assistant.
Drafted 2026-09-20 by Ronith Mugundakumar.
Surfaces: the Chainlit chat application mounted at `/chat` (`app/chainlit/chainlit_app.py`), and the conversation state and history it produces.

Defines how a conversation session is created, maintained, resumed and ended; how chat history is retained and made available; how the assistant behaves when a user starts, continues, resets or ends a conversation; and how prior turns feed into the answer for the current one. Requirement IDs are `SS-n` and are stable, per the traceability rule in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10.

**Status: pre-client-meeting.** Requirements marked `[ASSUMED]` need confirmation before they drive a sprint. The largest is retention: [`REQUIREMENTS.md`](REQUIREMENTS.md) DH-8 already warns that a retention period invented here could conflict with the firm's own obligations, so none is proposed. Section 10 carries it to the client meeting.

This document does not cover identity or login. That is [`LOGIN-PAGE-REQUIREMENTS.md`](LOGIN-PAGE-REQUIREMENTS.md), and section 3 states the boundary plainly so the two are never conflated.

Priorities are MoSCoW: **M** must, **S** should, **C** could.

## 1. Purpose and scope

Two things already exist with nothing behind them. [`REQUIREMENTS.md`](REQUIREMENTS.md) DH-7 requires that "questions and answers are retained so the firm can show what the tool said and what was done with it," and [`VALIDATION.md`](VALIDATION.md) section 2 has already validated a wireframe showing a "recent conversations list in the rail." Neither is implemented: `app/chainlit/chainlit_app.py` has no `cl.user_session` usage anywhere, no persisted history, and `generate_response()` answers every message as if it were the first one in the conversation. This document is where that gap gets defined before it gets built.

**In scope:** conversation (thread) creation and lifecycle within an already-authenticated session, persisted chat history and its retrieval and display, new-conversation and reset behaviour, assembling prior turns into context for the current answer, and the error handling specific to conversation state.

**Out of scope**, deliberately, not as backlog:

- Identity and login session - creation on sign-in, expiry, sign-out, cookies. That is [`LOGIN-PAGE-REQUIREMENTS.md`](LOGIN-PAGE-REQUIREMENTS.md) AU-39 to AU-47 and AU-83 to AU-87.
- The retention period itself. [`REQUIREMENTS.md`](REQUIREMENTS.md) DH-8 and open question 6 already flag this as a client question, not one this team answers by default.
- Role-based restriction of who may see whose history. Depends on AU-9's role answer, which is itself `[ASSUMED]`.
- What the assistant is allowed to say. That is [`REQUIREMENTS.md`](REQUIREMENTS.md) section 4 and [`PROMPTS.md`](PROMPTS.md); this document only says which prior turns reach the generator, not what it does with them.

## 2. What exists today

Stated plainly because the gap is the work.

| Component | Current state | Verified in |
|---|---|---|
| Conversation state | None. `@cl.on_chat_start` sends a static welcome. No `cl.user_session` is set or read anywhere in the codebase. | `app/chainlit/chainlit_app.py` |
| Multi-turn context | None. `@cl.on_message` calls `generate_response(message.content)` with a single string; no prior turns are passed in. Every answer is generated as if it were the first message in the thread. | `app/chainlit/chainlit_app.py`, `app/rag/generator.py` |
| Chat history persistence | None. No `conversations`, `messages`, or `threads` table exists. | `app/db/models.py`, `app/db/schema.sql` |
| Chainlit's own session config | `session_timeout = 3600` (reconnect grace period), `user_session_timeout = 1296000` (15 days), `confirm_new_chat = true`, `edit_message = true`. Generic Chainlit knobs, not application logic. | `.chainlit/config.toml` |
| UX expectation | A "recent conversations list in the rail" is already in the validated wireframes. | `VALIDATION.md` §2-3, CR-8 and the DH-7 finding |

The gap that matters most: the interface has already promised a feature - several retained, revisitable threads - that nothing in the backend can produce, and every answer today is generated with total amnesia of the previous turn even within one open browser tab.

## 3. Conversation session vs auth session

Two different things are called "session" in this system, and a build that treats them as one will get both wrong.

- The **auth session** is who is signed in. It is created at login, spans every page including `/chat`, and is owned entirely by [`LOGIN-PAGE-REQUIREMENTS.md`](LOGIN-PAGE-REQUIREMENTS.md) AU-39 to AU-47 and its Chainlit integration approach, AU-83 to AU-87. This document does not redefine, extend, or duplicate any of it.
- The **conversation session** is which thread of questions and answers a signed-in user is currently in, how long it is kept, and what history it carries. It exists only inside an auth session and cannot outlive one.

| SS | P | Requirement |
|---|---|---|
| SS-1 | M | A conversation session is scoped to exactly one auth session. It is never created, resumed, or read across two different signed-in identities. |
| SS-2 | M | Ending the auth session - sign-out, or expiry per AU-41 - ends every conversation session inside it. A conversation session is not a separate credential a user can carry after signing out. |
| SS-3 | M | This document's requirements never override or duplicate AU-39 to AU-47 or AU-83 to AU-87. Where a behaviour depends on identity or login state, this document names the requirement and points to it rather than restating it. |
| SS-4 | S | Conversation state (SS- below) and auth state (AU- in `LOGIN-PAGE-REQUIREMENTS.md`) are not held in the same table or the same session object, so a later change to one cannot silently affect the other. |

SS-3 is the rule most likely to be broken by whoever picks up both documents at once: the natural shortcut is to bolt chat-history fields onto whatever session object the login work introduces. AU-46 already settled that the chat surface and the FastAPI routes share one auth session; that decision says nothing about how many conversation threads that one auth session may hold, and conflating the two is the mistake this section exists to prevent.

## 4. Session lifecycle and creation

| SS | P | Requirement |
|---|---|---|
| SS-5 | M | A conversation thread is created the moment a signed-in user's first message in it is sent, not merely when the chat UI loads. Opening `/chat` with no interaction yet does not itself create a persisted thread. |
| SS-6 | M | Each thread carries a stable identifier and is bound to the account that created it (SS-1), never to a browser or a device. |
| SS-7 | M | Where the browser connection drops and reconnects within Chainlit's own `session_timeout` (currently 3600 seconds, `.chainlit/config.toml`), the same thread and any reply already in progress resume without creating a second thread or losing what was underway. |
| SS-8 | M | Beyond `session_timeout`, or after an explicit sign-out and sign-in, the user returns to a thread only by choosing it from their history (SS-14). Nothing resumes automatically into whichever thread happened to be open before. |
| SS-9 | S | A user may have more than one open, unfinished thread at a time. This document does not cap that number; the "recent conversations" rail already validated in `VALIDATION.md` assumes several. |
| SS-10 | M | A thread's creation time and owning account are recorded from the moment it is created, independent of whether any message in it has yet been answered, so DH-7 has something to report against even for a thread abandoned after one question. |

## 5. Chat history requirements

Covers DH-7 (retain what the tool said) and names where DH-8 (retention period) stays open rather than getting invented here.

| SS | P | Requirement |
|---|---|---|
| SS-11 | M | Every message a user sends and every reply the assistant returns within a thread are retained together as one turn, not as two independent records that can drift apart. |
| SS-12 | M | A retained turn includes the sources cited in the reply (per CH-1), not only the answer text, so DH-7's "what the tool said" is answerable in full, including what it was told. |
| SS-13 | M | A retained turn records which account it belongs to and when it happened. |
| SS-14 | M | A user can see and reopen their own past threads, each labelled well enough to recognise - the "recent conversations" list already committed to in `VALIDATION.md`. |
| SS-15 | S | Reopening a past thread loads its full turn history in order, not only the most recent turn. |
| SS-16 | M | No retention expiry is decided in this document. `[ASSUMED]` no automatic deletion runs until DH-8's period is agreed with the client; see section 10. |
| SS-17 | M | A user cannot delete their own history unilaterally. Whether removal is possible at all, and by whom, depends on the same retention answer as SS-16 - the two cannot be answered separately from each other. |
| SS-18 | C | A user can search or filter their own past threads by keyword or date, once there are enough retained to need it. |

## 6. New conversation behaviour

`.chainlit/config.toml` already sets `confirm_new_chat = true` - a confirmation prompt exists in the UI with nothing behind it to confirm.

| SS | P | Requirement |
|---|---|---|
| SS-19 | M | Starting a new conversation begins a new thread. It never overwrites or deletes the thread the user was previously in, the same "disable without deleting" discipline AU-61 applies to accounts. |
| SS-20 | M | The confirmation `confirm_new_chat` already shows must not claim data will be lost by starting a new thread, since it will not be - the copy has to match SS-19's actual behaviour. |
| SS-21 | M | A new thread starts with no context carried over from any prior thread. Conversation context (section 7) is scoped to one thread only. |
| SS-22 | M | The system does not start a new thread on its own initiative - on a timeout, an error, or a reconnect - without the user's action ending the previous one first. Losing track of a thread and ending it are not the same event. |
| SS-23 | S | A user can rename or otherwise re-label their own thread from the recent-conversations list, since a list of first-question-only labels degrades once several threads ask similar things. |

## 7. Conversation context requirements

`generate_response(query: str)` in `app/rag/generator.py` currently takes a single string. No requirement anywhere today describes how prior turns should reach it - this section is that requirement.

| SS | P | Requirement |
|---|---|---|
| SS-24 | M | Where a thread has prior turns, the answer to the current message is generated with those prior turns available as context, not as if it were the first message in the thread. |
| SS-25 | M | Context carried into a turn is limited to the current thread. A user's other threads never leak into it - this is what makes SS-19/SS-21 possible. |
| SS-26 | M | CH-1 (cite every claim), CH-2 (never combine law and firm procedure in one sentence), and CH-4 (state the income year) hold on turn 2, 3, and n of a thread exactly as they do on turn 1. A multi-turn answer is not exempt from `REQUIREMENTS.md` section 4. |
| SS-27 | M | Where the context assembled from prior turns exceeds what the model can be given, the oldest turns are dropped first. The current question and the sources retrieved for it are never dropped to make room. `[ASSUMED]` the exact budget is an implementation constant, not specified here. |
| SS-28 | S | Where a later question implicitly refers to an earlier one in the same thread ("what about for a company instead", "and last year?"), the answer resolves the reference from the thread's own context rather than asking the user to repeat themselves. Where it genuinely cannot be resolved, EC-8 applies: ask one clarifying question rather than guess. |
| SS-29 | M | Where an earlier turn's premise is shown superseded by what a later turn's sources say (EC-2), the correction happens on the later turn. An answer already given earlier in the thread is not silently rewritten. |
| SS-30 | C | A user can see, per answer, which prior turns in the thread were used as context for it. |

## 8. Error scenarios

Distinct from AU-67/AU-68, which cover an auth session expiring mid-question - that stays the login document's case. These are failures specific to conversation state.

| SS | P | Situation | Required behaviour |
|---|---|---|---|
| SS-31 | M | The history store is unavailable when a thread is opened | The message composer still works for a new question. The user is told past history could not be loaded, never shown an empty list that reads as "you have no history." |
| SS-32 | M | The history store is unavailable when a turn should be written | The answer is still shown in the live UI - per EC-12, no degraded or unsourced answer - but the user is told the turn may not be saved, rather than the write failing invisibly and the thread quietly losing it. |
| SS-33 | M | Generation fails partway through a turn | No half-written turn is retained. Either the complete question-and-answer pair is stored, or neither half is, per SS-11. |
| SS-34 | M | The same account has the same thread open in two tabs or devices at once | Both may read the thread's history. A message sent from one is visible in the other on next load. Concurrent sends do not corrupt turn order or overwrite each other. `[ASSUMED]` real-time sync between the two is not required; consistency on reload is. |
| SS-35 | S | A thread is reopened after the documents behind an earlier answer have changed or been withdrawn | The retained turn is shown as it was originally answered. It is not silently re-generated against the current corpus - doing so would misrepresent DH-7's "what the tool said" as something it never actually said. |
| SS-36 | M | A user attempts to open a thread that does not belong to their account | Treated as not found, not as an access-denied that confirms the thread exists - the same discipline AU-69 applies to `/testing`. |
| SS-37 | S | The account behind a thread is later disabled (AU-60) | The thread's history is retained per AU-61. A disabled account simply cannot sign in to view it again, which follows from SS-2 without any extra logic. |
| SS-38 | M | A message is sent in a thread whose auth session has already ended | Not this document's case to define. Handled by AU-67/AU-68; no conversation-session logic should attempt to duplicate that check. |

## 9. Data model implications

Stated as requirements rather than as a schema, because the schema is not this document's to write, and because `app/db/models.py` and `app/db/schema.sql` must be changed together per the contributing rule in [`README.md`](../README.md).

| SS | P | Requirement |
|---|---|---|
| SS-39 | M | A record exists for a conversation thread: an identifier, the owning account, and a created-at time (SS-6, SS-10). |
| SS-40 | M | A record exists for a turn: the thread it belongs to, its position within the thread, the question text, the answer text, the sources cited, and its own timestamp (SS-11 to SS-13). |
| SS-41 | M | A turn record retains the citation as it was given at the time, resilient to a later change to the underlying document (SS-35) - not a live reference re-resolved on read. |
| SS-42 | M | No conversation-state table duplicates or re-derives a field already owned by `app_users`. A turn's account reference is the same `app_users.id` foreign key AU-77 to AU-82 establish, not a second copy. |
| SS-43 | S | The schema supports listing a user's threads ordered by recency without scanning every turn - an index or a denormalised last-activity time on the thread record - since SS-14's list is read on every chat open. |
| SS-44 | M | No retention or deletion mechanism - column, job, or trigger - is added ahead of DH-8's client answer (SS-16). Adding one now would be inventing a policy this document explicitly refuses to invent. |

## 10. Open questions for the client

Each blocks or reshapes something above. To go to the meeting alongside the questions in [`CLIENT-MEETING-QUESTIONS.md`](CLIENT-MEETING-QUESTIONS.md).

| # | Question | Affects |
|---|---|---|
| 1 | How long should questions and answers be retained? | SS-16, SS-17, SS-44. Already open as question 6 in `REQUIREMENTS.md`; this document is where it stops being abstract. |
| 2 | Should a user be able to delete their own history, or only an administrator? | SS-17. Depends on question 1's answer as much as on firm policy. |
| 3 | Is a "recent conversations" list required for a first release, or can it support only the current open thread? | SS-14, SS-15, SS-18. Decides whether the persistence work in section 9 is a first-sprint item or can follow. |
| 4 | Should two devices signed in as the same person share visibility into each other's threads, or does each need its own? | SS-9, SS-34. Mirrors AU-70's open question about concurrent auth sessions. |

## 11. Traceability

| Source | Covered by |
|---|---|
| REQUIREMENTS.md DH-7, retention of what the tool said | SS-10 to SS-14, SS-40, SS-41 |
| REQUIREMENTS.md DH-8, retention period agreed with client, not assumed | SS-16, SS-17, SS-44, section 10 #1 |
| REQUIREMENTS.md CH-1, CH-2, CH-4, answer requirements | SS-12, SS-26 |
| REQUIREMENTS.md EC-2, correct a stale premise before answering | SS-29 |
| REQUIREMENTS.md EC-8, ask one clarifying question rather than guess | SS-28 |
| REQUIREMENTS.md EC-12, model or database unavailable | SS-31, SS-32, SS-38 |
| LOGIN-PAGE-REQUIREMENTS.md AU-39 to AU-47, AU-83 to AU-87, the auth session | Section 3, SS-1 to SS-4 |
| LOGIN-PAGE-REQUIREMENTS.md AU-46, one shared session across surfaces | SS-1 to SS-3 |
| LOGIN-PAGE-REQUIREMENTS.md AU-60, AU-61, disable without deleting history | SS-37 |
| LOGIN-PAGE-REQUIREMENTS.md AU-67, AU-68, auth session expiry mid-question | SS-38 |
| LOGIN-PAGE-REQUIREMENTS.md AU-69, access to a resource that is not yours | SS-36 |
| LOGIN-PAGE-REQUIREMENTS.md AU-70, concurrent sessions on two devices | SS-9, SS-34, section 10 #4 |
| LOGIN-PAGE-REQUIREMENTS.md AU-77 to AU-82, account record fields | SS-42 |
| VALIDATION.md CR-8 / DH-7 finding, recent conversations list in the rail | SS-14, SS-15, section 10 #3 |
| Task brief (board card, ticket 90), session lifecycle and creation | Section 4, SS-5 to SS-10 |
| Task brief, chat history requirements | Section 5, SS-11 to SS-18 |
| Task brief, new conversation behaviour | Section 6, SS-19 to SS-23 |
| Task brief, error scenarios | Section 8, SS-31 to SS-38 |
| Task brief, conversation context requirements | Section 7, SS-24 to SS-30 |
| Task brief, separate auth session from conversation session and name the owning doc | Section 3, SS-1 to SS-4 |

Nothing here is verified. These are proposed requirements for state that does not exist in the codebase yet, and the difference should stay visible in the sprint review rather than assumed.
