# Login page and authentication flow requirements

Team 83, Alfa Focus Knowledge Assistant.
Drafted 2026-09-14 by Ronith Mugundakumar. Integration approach added 2026-09-15.
Surfaces: the login screen, and every route in `app/main.py` that must sit behind it.

Defines what a user provides to sign in, how the system behaves on success and on failure, how a session is created and ended, and what must be true of the whole flow for the access requirements in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 6 to hold. Requirement IDs are `AU-n` and are stable, per the traceability rule in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10.

**Status: pre-client-meeting.** Requirements marked `[ASSUMED]` need confirmation before they drive a sprint. The biggest one is the authentication method itself: [`CLIENT-BRIEF.md`](CLIENT-BRIEF.md) section 3 assumes single sign-on, and nothing in the research confirms the firm has an identity provider to sign on to. Section 14 sets out what that changes.

The integration approach is not assumed. It was decided on 2026-09-15 and is recorded in section 2.1, because the build cannot begin without it and it does not depend on anything the client tells us.

Priorities are MoSCoW: **M** must, **S** should, **C** could.

## 1. Purpose and scope

Authentication exists here for one reason: five `M` requirements already agreed assert that only firm users reach this system, and none of them is currently true. DH-5 requires that only authenticated firm users reach the assistant or any of its pages. DH-6 requires that firm procedure content is unreachable outside the firm. UP-8 requires that only authorised firm users upload. EV-49 requires that `/testing` is reachable only by Team 83 and the reviewer accounts. Each of those is an access-control claim with no mechanism behind it.

The login flow is therefore not a feature of the product. It is the precondition that makes four other requirements checkable, and the thing a client will look for first when asked whether their material is safe in it.

**In scope:** the login screen, credential submission and verification, what happens on success and on failure, session creation and expiry, sign out, and the route guard that sends an unauthenticated request to the login screen rather than to content.

**Out of scope**, deliberately, not as backlog:

- Self-service registration. There is no public sign-up. Accounts are created by an administrator (section 11).
- Client or trustee accounts. Per [`REQUIREMENTS.md`](REQUIREMENTS.md) section 1, no interface is used directly by the firm's clients.
- Per-document or per-corpus permissions. DH-10 is `C` priority and depends on client policy we have not seen.
- Any change to what the assistant says once a user is signed in. That is [`PROMPTS.md`](PROMPTS.md) and [`REQUIREMENTS.md`](REQUIREMENTS.md) section 4.

**Relationship to the earlier login work.** A mock-sprint requirements document from week 4, `team-83-login-restyling.md`, fixed a login change as styling-only and listed the behaviours a restyle may not alter: the credential flow, session creation and duration, the post-login redirect, the route guards, and the mapping of error condition to message. That list was written against a login screen that does not exist in this repository, and the document itself is not in this repository either. This document is where those behaviours are defined for the first time; the styling-only boundary applies to changes made after the flow is built, not before.

## 2. What exists today

Stated plainly because the gap is the work.

| Component | Current state | Verified in |
|---|---|---|
| Login screen | None. `GET /` redirects straight to `/chat`. | `app/main.py` |
| Credential store | `app_users` holds `id`, `email`, `role`, `created_at`. There is no password field, no status field, and no record of a last sign-in. | `app/db/models.py`, `app/db/schema.sql` |
| Chat authentication | None registered. Chainlit is public by default and becomes private only when `CHAINLIT_AUTH_SECRET` is defined and an auth callback is added. Neither exists. | `app/chainlit/chainlit_app.py`, `app/config.py`, `.env.example` |
| Route guards | None. `/home`, `/upload` and `/testing` are served without any check. | `app/main.py`, `app/routes/` |
| API documentation | `FastAPI()` is constructed with defaults, so `/docs` and `/openapi.json` are public and enumerate every route. `README.md` lists `/docs` as a normal endpoint. | `app/main.py`, `README.md` |
| Cross-origin policy | `allow_origins = ["*"]`. | `.chainlit/config.toml` line 23 |

The two-surface problem in that table is the one to design around rather than discover. The chat interface is a Chainlit application mounted into FastAPI, and the upload and testing pages are ordinary FastAPI routes. Authenticating one does not authenticate the other. A build that adds a Chainlit auth callback and stops there leaves `/upload` open, which satisfies DH-5 for the assistant and breaks UP-8 in the same commit.

### 2.1 Decided integration approach

Decided 2026-09-15. Recorded here because the approach determines what sections 5 to 11 mean in practice, and because leaving it to whoever picks up the build produces the half-authenticated state described above.

`app/main.py` calls `mount_chainlit(..., path="/chat")`, which resolves to `app.mount("/chat", chainlit_app)`. Chainlit is therefore a complete second web application running inside this one, with its own routes and its own middleware. Three mechanisms in it matter to the decision, all read from Chainlit's source rather than from its documentation:

- It signs its own session as a JWT using HS256 with `CHAINLIT_AUTH_SECRET`, carrying the user plus `exp` and `iat`, and stores it in an `HttpOnly` cookie named `access_token`.
- Its `header_auth_callback` receives the full request headers, which includes the `cookie` header, and returns a user or nothing.
- It is public until `CHAINLIT_AUTH_SECRET` is set and a callback is registered.

The second of those is what makes the approach below possible: an application that already knows who the user is can tell Chainlit, rather than asking the user to sign in twice.

| AU | P | Requirement |
|---|---|---|
| AU-83 | M | The login screen and the session are owned by the FastAPI application. Chainlit does not perform the credential check. |
| AU-84 | M | Chainlit accepts the already-established identity through its header auth callback, reading the session cookie from the request headers. |
| AU-85 | M | An application-wide middleware guard rejects unauthenticated requests before they reach any route, so a route added later is protected without its author writing anything. Per-route checks are not sufficient, because the failure mode is a route nobody remembered to decorate. |
| AU-86 | M | `CHAINLIT_AUTH_SECRET` is set in every environment. Chainlit serves the chat to anyone until it is. |
| AU-87 | S | Any Chainlit token issued after the header check succeeds is ended by the same sign out that ends the FastAPI session, per AU-43. Two tokens in the browser is an accepted consequence of this approach; two live sessions after sign out is not. |

These IDs are numbered from the end of the document rather than inserted here, so that no existing ID shifts. That is the traceability rule in [`REQUIREMENTS.md`](REQUIREMENTS.md) section 10 applied to this document.

The alternative was to let Chainlit own the login and have FastAPI verify its cookie. It is less work, and it was rejected because the login screen would then be Chainlit's built-in one, configurable only to the extent its settings allow, which is roughly a background image. AU-26 through AU-29 describe redirect and role behaviour that a built-in screen will not provide, and the wireframes in [`VALIDATION.md`](VALIDATION.md) already commit to a signed-in identity and role in the rail. Owning the screen is the reason for the extra work, not an accident of it.

Verify all three mechanisms above against the pinned `chainlit==2.11.0` in `requirements.txt` before building on them. They were read from the current source on the project's main branch, and the cookie name, the chunking behaviour above 3000 characters, and the helper names may differ in the pinned release.

## 3. Surfaces behind authentication

| AU | P | Surface | Required access |
|---|---|---|---|
| AU-1 | M | `/chat` | Any authenticated firm user. |
| AU-2 | M | `/upload` | Authenticated firm users with the upload permission, per UP-8. Until roles are confirmed with the client, `admin` only. `[ASSUMED]` |
| AU-3 | M | `/testing` | Team 83 accounts and the reviewer accounts created for judge validation, per EV-49. Not firm staff. Not linked from any signed-in firm view. |
| AU-4 | M | `/home` and any other rendered page | Any authenticated firm user. No page is served to an anonymous request. |
| AU-5 | M | `/docs` and `/openapi.json` | Disabled in the deployed environment, or placed behind the same authentication. A public schema listing of `/upload` and `/testing` contradicts DH-5 whether or not those routes are themselves guarded. |
| AU-6 | M | The login screen and its static assets | The only surface reachable without a session. |

AU-3 is the one most likely to be got wrong, because `/testing` is the only route whose authorised users are not firm staff. It has two exclusions, not one: firm users must not reach it, and it must not appear in firm navigation. The first is authorisation and the second is a design constraint, and satisfying only the first still shows an accountant a link to a page they cannot open.

## 4. Users and roles

| AU | P | Requirement |
|---|---|---|
| AU-7 | M | Every account belongs to exactly one named person. No shared or role accounts, because DH-7 requires the firm to be able to show what the tool said and who acted on it, and a shared login makes that unanswerable. |
| AU-8 | M | Each account carries a role. The roles in the current schema are `staff` and `admin`. |
| AU-9 | M | `staff` may use the assistant. `admin` may additionally upload, withdraw documents, and manage accounts. `[ASSUMED]` pending client answer on who may upload. |
| AU-10 | S | Team 83 and validation reviewer accounts are distinguishable from firm accounts, so that EV-49 can be enforced by role rather than by an allowlist of addresses that will not survive handover. |

The role split in AU-9 is an inference from [`REQUIREMENTS.md`](REQUIREMENTS.md) open question 5 and is written broadly on purpose. Do not add a third role to fill it in before the client has answered.

## 5. Login fields

Fields a user provides. The set is deliberately minimal: NF-2 requires an accountant to be able to use the system after a short walkthrough, and NF-6 requires the firm to run it with no IT staff.

| AU | P | Field | Type | Required | Notes |
|---|---|---|---|---|---|
| AU-11 | M | Email address | text, `type="email"`, `autocomplete="username"` | Yes | The identifier. `app_users.email` is already unique, so it is the natural key and no separate username is introduced. |
| AU-12 | M | Password | text, `type="password"`, `autocomplete="current-password"` | Yes | Masked by default. |
| AU-13 | S | Show or hide password | toggle | No | Defaults to hidden. Reduces mistyping on a long password, which is the failure the lockout in AU-49 punishes. |
| AU-14 | C | Keep me signed in | checkbox | No | Unchecked by default. Only extends the session to the longer duration in AU-41; it never removes expiry. Do not build it until AU-41 has a client-agreed number. |
| AU-15 | M | Submit | button | Yes | Disabled while a submission is in flight, so a double click cannot count as two failed attempts against AU-49. |
| AU-16 | S | Support contact | static text | No | Names who to contact when a user cannot sign in. With no help desk at the firm, a user locked out of a screen that offers no next step will email whoever set it up, and that person will not be on the team after handover. |

No field on this screen collects anything about a member or a fund. The client identifier warning required by DH-3 belongs at the message composer, not here, and adding it to the login screen would train users to ignore it where it matters.

## 6. Input validation

Validation on this screen decides whether a submission is worth checking, not whether the credentials are right. Everything in this section runs before any lookup.

| AU | P | Requirement |
|---|---|---|
| AU-17 | M | Both fields are required. An empty field is reported against that field before any request is sent. |
| AU-18 | M | The email field is trimmed of leading and trailing whitespace and compared case-insensitively. `Rachel@alfafocus.com.au` and `rachel@alfafocus.com.au` are the same account. |
| AU-19 | M | The password is never trimmed, never case-folded, and never normalised. A password is the bytes the user typed. |
| AU-20 | M | The email must be structurally valid before a request is sent. A structurally invalid address is a format error shown against the field, not a failed sign-in attempt, and does not count toward AU-49. |
| AU-21 | M | Maximum lengths are enforced on both fields, at the server as well as in the browser. Client-side length limits are a usability feature; the server limit is what stops an unbounded input reaching the hashing function. |
| AU-22 | M | Every rule in this section is enforced server-side regardless of what the browser did. A request that bypasses the form is subject to the same checks. |
| AU-23 | S | Validation messages appear against the field they concern and do not clear the other field's contents. Re-entering a correct email because the password was wrong is the fastest way to cause a lockout. |

AU-20 is the distinction that matters most here. A typed address with no `@` is a mistake the user can see and fix, and telling them so costs nothing. A well-formed address that does not exist is a different thing entirely, and section 8 requires it be treated as a failed sign-in with no hint about which half was wrong.

## 7. Successful login behaviour

| AU | P | Requirement |
|---|---|---|
| AU-24 | M | On a correct credential pair for an active account, the system creates a session bound to that account and its role, and the user reaches signed-in content without re-entering anything. |
| AU-25 | M | The user lands on the assistant at `/chat` by default. |
| AU-26 | M | Where the user arrived at the login screen by requesting a specific page while signed out, they land on that page instead, provided their role permits it. A user who bookmarked `/upload` should not have to navigate back to it. |
| AU-27 | M | The redirect target in AU-26 is validated against a list of the application's own routes. A target supplied in the request and followed without checking is an open redirect, which turns the login page into a credible phishing landing point for an audience that has been told to trust it. |
| AU-28 | M | Where the user's role does not permit the requested page, they land on `/chat` and are told the page was not available to them. They are not told the page does not exist, and they are not left on a blank screen. |
| AU-29 | M | The signed-in identity and role are visible on every signed-in page, alongside a sign out control, per CR-8 in [`VALIDATION.md`](VALIDATION.md) section 1. This is how a user in a firm with shared workstations can tell whose session they are in before they type a question into it. |
| AU-30 | S | The session records the sign-in time and the account it belongs to, so that DH-7 has something to report against. |
| AU-31 | C | The account's last successful sign-in is shown to the user on arrival. It is the cheapest control available for noticing a session that was not theirs. |

## 8. Failed login behaviour

| AU | P | Situation | Required behaviour |
|---|---|---|---|
| AU-32 | M | Email not found | The same message, the same field treatment and the same response time as a wrong password. See below. |
| AU-33 | M | Password wrong | One message that names neither field as the wrong one: the credentials were not recognised. |
| AU-34 | M | Account disabled | Told plainly that the account is not active and who to contact. This is distinguishable from AU-32 and AU-33 only after the credentials are correct, never before. |
| AU-35 | M | Account locked by AU-49 | Told that the account is temporarily locked, and when it will unlock or what to do. A lockout the user cannot distinguish from a wrong password produces repeated attempts that extend it. |
| AU-36 | M | Database or identity provider unavailable | A plain failure message saying sign-in is unavailable and to try again shortly. Never a stack trace, never a partial sign-in, and never a fallback that admits the user without verification. This is EC-12 applied to the front door. |
| AU-37 | M | Any failure | The password field is cleared, the email field is not, and focus returns to the password field. |
| AU-38 | S | Any failure | The response time does not reveal which failure occurred. An unknown address that returns in 20ms while a real one returns in 300ms enumerates the firm's staff list to anyone who cares to measure. |

AU-32 and AU-33 return the same message on purpose, and it will be challenged in review as unhelpful. It is: the alternative tells an unauthenticated stranger which email addresses are real accounts at an accounting firm, which is the first step of every credential attack that follows. The firm's addresses follow a visible pattern at a known domain, so this is not a theoretical exposure.

## 9. Session and sign-out

| AU | P | Requirement |
|---|---|---|
| AU-39 | M | A session is represented by a signed token or a server-side session identifier. The client is never trusted to assert its own identity or role. |
| AU-40 | M | The role used for every authorisation decision is read from the server's record of the session, not from anything the browser sends. A role in a token the browser can edit is a suggestion. |
| AU-41 | M | Sessions expire. An idle session ends after a defined period and an absolute maximum lifetime applies regardless of activity. `[ASSUMED]` The two numbers need client agreement; see section 14. |
| AU-42 | M | The session cookie is `HttpOnly`, `Secure`, and `SameSite=Lax` or stricter. |
| AU-43 | M | Sign out is available on every signed-in page and ends the session at the server, not only in the browser. Clearing a cookie while the token stays valid is not signing out. |
| AU-44 | M | After sign out, the back button does not restore signed-in content. Signed-in pages are not stored in the browser cache. |
| AU-45 | M | A new session identifier is issued at the moment of successful sign-in, replacing any identifier the visitor already had. |
| AU-46 | M | The chat surface and the FastAPI routes share one session, established once per sign-in. A user signs in once and reaches both. Two logins for one application is a support burden at a firm with no IT staff and makes it impossible to state plainly who is signed in. |
| AU-47 | S | An expired session on the chat surface is reported as an expired session and returns the user to sign in. It does not surface as a failed message send or a connection error. |

AU-46 is the requirement the rest of this document hangs on, which is why it is `M` rather than a consistency preference. It is where the two-surface problem in section 2 is resolved, and section 2.1 names the mechanism. A build that produces two sessions is not a smaller version of this; it is a different product, and it is one where `/upload` is reachable by anyone who knows the URL.

## 10. Security requirements

| AU | P | Requirement |
|---|---|---|
| AU-48 | M | Passwords are stored only as a salted hash from a current password-hashing function with a deliberate work factor. The plaintext is never stored, never logged, and never written to an error report. |
| AU-49 | M | Repeated failed attempts against one account are rate limited and the account is temporarily locked after a defined threshold. The threshold and lock duration are configuration, not constants in the code. |
| AU-50 | M | Repeated failed attempts from one source are rate limited independently of the account, so that one attempt against each of many accounts is also constrained. |
| AU-51 | M | All authenticated traffic is over HTTPS. The login form is never served or submitted over plain HTTP. |
| AU-52 | M | No secret, password, token, or connection string is committed. `CHAINLIT_AUTH_SECRET`, the session signing key and any identity-provider credential are environment configuration and are added to `.env.example` as names with no values, per DH-9. |
| AU-53 | M | Authentication events are logged: the attempt, the account, the outcome, the time and the source. The password is not logged on any path, including the failure path. |
| AU-54 | M | The application does not expose its own route inventory to an unauthenticated request, per AU-5. |
| AU-55 | M | `allow_origins = ["*"]` in `.chainlit/config.toml` is replaced with the deployed origin before authentication ships. A permissive origin policy in front of an authenticated session undoes part of what the session is for. |
| AU-56 | S | A password minimum length is enforced at the point a password is set, with length preferred over composition rules. Composition rules produce predictable passwords and a firm with no IT support will not survive a rotation policy. |
| AU-57 | S | Changing a password ends all other sessions for that account. |
| AU-58 | C | Multi-factor authentication. Not in the first build, and named here so its absence is a decision rather than an omission. Worth raising with the client, because the material behind this login is the firm's own procedure content. |

AU-52 has a dependency the team will hit on the first day of the build: `CHAINLIT_AUTH_SECRET` does not exist in `.env.example` or `app/config.py`, and Chainlit is public until it does. Adding it is part of this work, not a follow-up.

## 11. Account lifecycle

| AU | P | Requirement |
|---|---|---|
| AU-59 | M | An administrator can create an account with an email and a role without developer involvement. NF-6 fails immediately if adding a staff member requires a code change. |
| AU-60 | M | An administrator can disable an account. A disabled account cannot sign in and its existing sessions end. |
| AU-61 | M | Disabling an account does not delete its history. DH-7 requires the firm to show what the tool said; deleting the user who asked removes half of that. |
| AU-62 | M | The first administrator account is created by a documented, deliberate step. It is not a default credential pair in the repository, and it is not created automatically on first run. |
| AU-63 | S | A user can change their own password. |
| AU-64 | S | An administrator can reset a password for a user who cannot sign in. With no help desk at the firm, the alternative is a developer running SQL against production, which does not survive handover. |
| AU-65 | C | Self-service password reset by email. It needs an email-sending path the project does not currently have. |

AU-62 is the requirement most likely to be satisfied with a seeded `admin@alfafocus.com.au` / `admin` pair during development, which then reaches the deployed environment because nothing in CI looks for it. Write the check before the seed.

## 12. Edge cases

| AU | P | Situation | Required handling |
|---|---|---|---|
| AU-66 | M | An unauthenticated request arrives at a deep link such as `/upload` | Redirect to the login screen, retain the requested path, and honour it after sign-in per AU-26 and AU-27. |
| AU-67 | M | A session expires while the user is reading an answer | The answer stays on screen. The next action reports an expired session and returns them to sign in. Nothing they typed is submitted to a system that no longer knows who they are. |
| AU-68 | M | A session expires mid-question, before the answer returns | The question is not silently discarded and is not answered. The user is told the session expired and the question is preserved in the composer where possible. |
| AU-69 | M | A firm user follows a link to `/testing` | Not authorised, handled per AU-28. The page's existence is not confirmed to them and no evaluation content is rendered. |
| AU-70 | M | The same account signs in from a second device | Both sessions are valid. Sign out ends the session it was invoked from, not the other. `[ASSUMED]` Concurrent sessions are normal at a firm with a desktop and a laptop; confirm the client does not want them restricted. |
| AU-71 | M | An account is disabled while it holds a live session | The session ends at the next request. A disabled account that keeps working until its token expires is not disabled. |
| AU-72 | M | The database is unavailable at the moment of sign-in | AU-36. Fail closed with a plain message. There is no degraded mode in which access is granted without verification. |
| AU-73 | S | A user signs in on a shared workstation and walks away | Covered by AU-41 idle expiry and by AU-29 showing whose session it is. Neither is sufficient alone. |
| AU-74 | S | A user submits the form twice quickly | One attempt is counted. AU-15 disables the control in flight and the server treats a duplicate submission of the same credentials within a short window as one attempt. |
| AU-75 | S | A signed-in user opens the login screen again | They are sent to the assistant rather than shown a form. A login screen presented to an already-authenticated user reads as a session that was lost. |
| AU-76 | C | A user's browser blocks cookies | A plain message explaining that sign-in requires cookies. A silent redirect loop back to the login screen is the default behaviour and is indistinguishable from a wrong password. |

AU-68 is worth a test of its own. The chat surface holds a long-running request, and the natural implementation checks the session when the message is sent but not when the answer is written back. The failure mode is an answer delivered into a session that has ended, which is the one outcome every requirement in section 9 exists to prevent.

## 13. What the data model must hold

`app_users` as it stands cannot support any of the above. The gaps below are stated as requirements rather than as a schema, because the schema is not this document's to write, and because `app/db/models.py` and `app/db/schema.sql` must be changed together per the contributing rule in [`README.md`](../README.md).

| AU | P | Requirement |
|---|---|---|
| AU-77 | M | The account record holds a password hash. There is no password field today, so no credential can be verified against the current schema. |
| AU-78 | M | The account record holds an active or disabled status, so AU-60 and AU-71 are expressible. A deleted row is not a disabled account, because deleting it breaks AU-61. |
| AU-79 | M | The account record holds the failed-attempt count and the lock expiry that AU-49 needs, or these live in a store the application can read and reset atomically. |
| AU-80 | S | The account record holds the last successful sign-in time, for AU-31 and AU-53. |
| AU-81 | S | Authentication events are recorded in their own table rather than only in application logs, since DH-7 is a reporting requirement and a log file on Render is not queryable evidence. |
| AU-82 | M | The role values are constrained to the agreed set. The column is free text today, so a typo produces an account with a role nothing authorises and no error anywhere. |

## 14. Open questions for the client

Each blocks or reshapes something above. To go to the meeting alongside the questions in [`CLIENT-MEETING-QUESTIONS.md`](CLIENT-MEETING-QUESTIONS.md).

| # | Question | Affects |
|---|---|---|
| 1 | Does the firm have Microsoft 365, Google Workspace, or any identity provider staff already sign in to? | The whole of sections 5 to 10. With an identity provider, most of this document becomes a redirect and the password requirements fall away. Without one, we own password storage, lockout and reset. [`CLIENT-BRIEF.md`](CLIENT-BRIEF.md) section 3 assumes single sign-on on `LOW` confidence evidence and section 4 records that the firm's own website is not serving, so the assumption cannot stand on its own. |
| 2 | Who may upload documents, and who may see firm procedure content? | AU-2, AU-9, and DH-6, DH-10, UP-8. Already open as question 5 in [`REQUIREMENTS.md`](REQUIREMENTS.md); authentication is where it stops being abstract. |
| 3 | How long should a session last before it expires, and is an idle timeout acceptable on a shared workstation? | AU-41. A number we invent is either an irritation or a control that does nothing. |
| 4 | How long are sign-in records retained? | AU-53, AU-81, and DH-8. DH-8 already warns that a retention period we invent could conflict with the firm's own obligations. |
| 5 | Is multi-factor authentication expected for a tool holding the firm's internal procedure? | AU-58. Cheap to answer now, expensive to retrofit after handover. |
| 6 | Who administers accounts after handover, given there is no IT staff? | Section 11. If the answer is nobody, AU-59 and AU-64 need to be usable by an accountant, and that changes the design rather than the priority. |

`[ASSUMED]` Question 1 is currently assumed to be no, so this document specifies password authentication the project owns. That is the safer default: building password auth when an identity provider exists wastes a sprint, while assuming an identity provider that does not exist leaves the system with no authentication at all.

## 15. Traceability

| Source | Covered by |
|---|---|
| REQUIREMENTS.md DH-5, only authenticated firm users reach the assistant | AU-1, AU-4, AU-6, AU-66 |
| REQUIREMENTS.md DH-6, firm procedure not reachable outside the firm | AU-1 to AU-5, AU-39 to AU-45 |
| REQUIREMENTS.md DH-9, credentials in environment configuration | AU-52 |
| REQUIREMENTS.md DH-7, retention of what the tool said | AU-7, AU-30, AU-53, AU-61, AU-81 |
| REQUIREMENTS.md UP-8, only authorised firm users upload | AU-2, AU-9, AU-40 |
| REQUIREMENTS.md EC-12, model or database unavailable | AU-36, AU-72 |
| REQUIREMENTS.md NF-2 and NF-6, usable and handover-able | AU-11 to AU-16, AU-59, AU-64, AU-65 |
| TESTING-PAGE-REQUIREMENTS.md EV-49, `/testing` access isolation | AU-3, AU-10, AU-69 |
| VALIDATION.md CR-8, signed-in user and sign out in the rail | AU-29, AU-43 |
| Task brief, purpose and scope of authentication | Sections 1 to 3 |
| Task brief, required login fields | AU-11 to AU-16 |
| Task brief, input validation | AU-17 to AU-23 |
| Task brief, successful login behaviour | AU-24 to AU-31 |
| Task brief, unsuccessful login attempts | AU-32 to AU-38 |
| Task brief, how authentication connects to the user session | AU-39 to AU-47, AU-83 to AU-87 |
| Task brief, basic security requirements | AU-48 to AU-58 |
| Checklist item, record the integration approach | Section 2.1, AU-83 to AU-87 |

Nothing here is verified. These are proposed requirements for a flow that does not exist, and the difference should stay visible in the sprint review. Note also that [`VALIDATION.md`](VALIDATION.md) sections 6 and 8 reference a `TRACEABILITY.md` that is not in the repository; until it is, the `M` requirements above have no verification record anywhere, and the same is true of the access-control requirements they inherit from.
