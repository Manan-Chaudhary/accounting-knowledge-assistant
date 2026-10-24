# Client Brief - Alfa Focus

Compiled 2026-08-17 from open-source research only. **No client contact has occurred** (the client was never met by project end, so nothing below was confirmed and every `MEDIUM` and `LOW` line is still unverified). Confidence markers are load-bearing: do not promote a `MEDIUM` or `LOW` line to a statement of fact in the proposal.

Confidence scale:
- `HIGH` - multiple independent sources, or a government register
- `MEDIUM` - one credible source, plausible and internally consistent
- `LOW` - scraped/aggregator data, stale, or contradicted elsewhere

## 1. Identity and registration

| Fact | Value | Confidence | Source |
|---|---|---|---|
| Trading name | Alfa Focus | HIGH | multiple |
| Business address | Suite 42, 68-72 York Street, South Melbourne VIC 3205 | HIGH | [HotFrog listing](https://www.hotfrog.com.au/company/1072162831618048), corroborated by directory results |
| Phone | 03 9674 0335 | MEDIUM | HotFrog listing (unclaimed, 0 reviews) |
| Domain | alfafocus.com.au | HIGH | referenced by every directory and by staff email domains |
| Tax agent registration | "Alfa Focus Pty Ltd", Company Tax Agent, agent number 24717632, registered 15/04/2014 | MEDIUM | [search-afsl.com TPB mirror](https://search-afsl.com/Alfa%20Focus%20Pty%20Ltd/tpb/1070170/) - a third-party mirror, not the TPB itself |
| ABN | 82 823 248 780 - "Alfa Focus" (trading name) and "The trustee for Alfa Focus Unit Trust", both active, **postcode VIC 3127** | MEDIUM | [ABN Lookup](https://abr.business.gov.au/Search/ResultsActive?SearchText=Alfa%20Focus) |

### Unresolved discrepancy - flag at the first meeting

The ABN register puts "Alfa Focus" in **postcode 3127** (Camberwell/Canterbury), while every business directory and the TPB mirror put the practice in **South Melbourne 3205**. Two readings:

1. The unit trust is the registered proprietor with a registered-office address in 3127, and 3205 is the trading premises. Common and unremarkable.
2. There are two distinct entities, and "Alfa Focus Pty Ltd" (the tax agent) is not the same legal person as "The trustee for Alfa Focus Unit Trust".

This matters for the project only insofar as an engagement letter, a data-processing agreement, or an ethics/privacy statement has to name the right entity. Confirm it; do not guess it in a written deliverable.

**Verification not yet done:** the TPB public register at `tpb.gov.au/public-register` timed out on 2026-08-17. Confirm the agent number and current registration status directly against the TPB before citing it. A third-party mirror is not evidence of *current* registration.

## 2. What the firm actually does

`HIGH` - consistent across every source that describes them:

> A Chartered Accounting firm offering a complete accounting and administration service for Self Managed Superannuation Funds and their trustees.

Concretely, the service lines described are:

1. **SMSF establishment** - creating the fund, trust deed, member and trustee structure.
2. **End-to-end SMSF administration** - the ongoing bookkeeping, data feeds, and reconciliations that keep a fund current.
3. **Compliance and reporting** - annual financial statements, the SMSF annual return (SAR), member statements.
4. **Arranging the independent audit** - every SMSF must be audited annually by an ASIC-approved SMSF auditor who is independent of the accountant preparing the accounts. Alfa Focus arranges rather than performs it.
5. **Strategic advice** in tax, superannuation, and **property in super, specifically borrowing to acquire property** - i.e. limited recourse borrowing arrangements (LRBAs).

### The part that reframes the project

Their stated market is not only direct trustees. It is explicitly:

> SMSF Trustees, Financial Planners & Accountants who are looking to out-source the administration of their own or their client's SMSF.

So a meaningful share of the client base is **other professionals**. That has three consequences for the assistant:

- The questions arriving at the firm are already semi-technical. Our users are not laypeople asking "what is super" - they are accountants asking "does the in-house asset rule bite here".
- Volume and repetition are high. B2B outsourcing means the same twenty compliance questions recur across hundreds of funds. That is a very good fit for retrieval, and a very good source of benchmark questions.
- Answer consistency across staff is a business asset. If two accountants at Alfa Focus give a referring financial planner different answers, the firm loses the referral. **"Consistency" is a stronger business case for this client than "speed"** - worth saying in the proposal, because it is not the pitch they will expect.

**Alfa Focus is a generalist tax and accounting firm** (confirmed by the team, not by the client). The directory research below found SMSF administration prominently advertised, so SMSF is one major service line, but the firm's work is not limited to it. The corpus is currently weighted towards SMSF material (see `DOCUMENT-CORPUS.md`); general tax and business content is the area to widen next.

## 3. People

`LOW` - all of the following comes from ZoomInfo, which scrapes and does not verify, and gives no date. Treat as a hypothesis about the org chart, useful only for planning who to interview.

| Name | Title as listed |
|---|---|
| Khoi Vu | Chief Executive Officer |
| Rachel Ruan | Senior Accountant |
| Iris Wang | SMSF Accountant |
| Stephanie Hoang | Customer Service Manager |
| John Ovens | (title not surfaced) |

Read cautiously, this suggests a **small practice, roughly 5-15 people**, with a service-delivery layer (SMSF accountants) under a principal, plus a client-facing coordination role. If that shape is right, the implications are large:

- There is no IT department. Whatever ships has to be operable by an accountant, not maintained by an engineer. This is the strongest argument for a plain chat page behind a login that needs no training. The built system is a React chat page (`/assistant`) with email and password sign-in; there is no SSO.
- There is probably no formal knowledge base to ingest. Firm knowledge lives in senior heads, in email, and in the file notes on individual funds. **Corpus B may have to be created during the project, not merely indexed.** This is the single biggest delivery risk in the whole engagement.
- A "Customer Service Manager" role suggests inbound client queries are a recognised workload with an owner. That person is the best interview subject for benchmark questions - they see the real question distribution.

## 4. Digital maturity

`HIGH`, and worth stating plainly because it shapes what can be deployed:

- **The main website is not serving.** `alfafocus.com.au` returned a 503 over HTTP and a failed TLS handshake over HTTPS, tested 2026-08-17 from two independent networks.
- **A WordPress site exists at [alfafocus.wordpress.com](https://alfafocus.wordpress.com/) and was never finished.** It still carries the theme's placeholder content: a San Diego, California address, a `1-202-555-1212` phone number, and stock testimonials from fictional restaurant executives. Its three real blog posts are SMSF explainers dated November 2018.
- **The HotFrog directory listing is unclaimed**, uncategorised, and has no description.

Do not put this in a client-facing document as a criticism. Do use it internally to calibrate:

1. Expect no existing stack to integrate with. The Supabase-backed system in this repo is not competing with anything. (It is not deployed: it runs locally on Docker Compose.)
2. Expect authentication, hosting, and data governance to be *our* problem to specify, because nobody there will specify it for us.
3. Expect the deliverable that survives is the one an accountant can open and use on day one.
4. The 2018 blog posts are the only public artefacts of their voice. Thin, but they are a real sample of how the firm explains SMSF concepts.

## 5. Likely software stack

`LOW` - inferred from the Australian SMSF administration market, not from any Alfa Focus source. Confirm at the meeting; this determines whether Corpus B can be indexed at all.

Australian SMSF administration is dominated by two platforms - **BGL Simple Fund 360** and **Class Super** - with Xero or MYOB commonly alongside for any general-practice work, and a document/workflow layer (FYI, SuiteFiles, or a plain network drive). Ask which, and ask whether it has an API. The answer decides whether "how does Alfa Focus do X" can be answered from structured process data or only from interviews.

## 6. What the assistant is for, restated in the client's terms

The stated purpose is to help the accountants with (a) ever-evolving accounting practice and (b) how Alfa Focus specifically would execute something. Mapped onto what this firm is:

| User need | Real example for this firm | Which corpus |
|---|---|---|
| Keep up with change | "Division 296 starts 1 July 2026 - which of our funds are affected and what do we have to report?" | A |
| Apply a rule to a case | "Trustee wants to buy a commercial property through the fund with a loan. What are the LRBA conditions?" | A |
| Follow the firm's method | "What is our checklist before we send a fund to audit?" | B |
| Reproduce a precedent | "How did we handle the last in-house asset breach we found?" | B |
| Answer a referrer | "A planner is asking whether their client can start a pension at 63 with a $3.4m balance" | A, multi-hop |

The second and fourth rows are where the value is, and they are the rows that need Corpus B to exist. Push hard on that in the first meeting - see [`CLIENT-MEETING-QUESTIONS.md`](CLIENT-MEETING-QUESTIONS.md) Q3.

## 7. Research gaps

- TPB register not directly confirmed (site timed out).
- No ASIC company extract pulled - would settle the entity question in section 1.
- No archived copy of the live site obtained; `web.archive.org` is not reachable from the research toolchain.
- No LinkedIn company page found, so headcount remains an inference.
- Nothing known about client volume, fund count, staff count, or query volume. All of these are proposal inputs.
