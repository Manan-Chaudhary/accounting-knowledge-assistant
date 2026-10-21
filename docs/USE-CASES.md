# Accounting Use Cases for the Chatbot

> **Status: research, `[ASSUMED]`.** The use cases were inferred from public research; Alfa Focus was never met, so none was confirmed. The built system does not special-case any of them: all are served by the same retrieval and prompt, and the 73-document corpus covers all seven (`DOCUMENT-CORPUS.md` section 2). Firm-procedure questions (use case 7's C5) cannot be answered because no Corpus B exists.

Research task: identify specific accounting use cases the assistant should handle, grounded in Alfa Focus's actual service offering rather than accounting generally. Source material: [`CLIENT-BRIEF.md`](CLIENT-BRIEF.md), [`DOMAIN-PRIMER.md`](DOMAIN-PRIMER.md), [`REQUIREMENTS.md`](REQUIREMENTS.md).

**Scoping note:** Alfa Focus is an SMSF-only Chartered Accounting firm (`CLIENT-BRIEF.md` section 2), not a general tax practice - this is not yet confirmed with the client (`REQUIREMENTS.md` open question 1). So of the example themes in the card (small business CGT concessions, inheritance, cross-border/residency, FBT, Division 7A), only the ones that genuinely show up in SMSF work are included below as primary use cases. The others are noted at the bottom as out of scope until the client confirms whether a general tax book exists.

Each use case below lists: what it covers, why it fits Alfa Focus, the question themes within it, and the question types (using the C1-C7 classes already defined in [`EVALUATION.md`](EVALUATION.md) section 2) it should be tested with.

---

## 1. SMSF compliance and investment restrictions

What it covers: sole purpose test, in-house asset rule (5% cap), related-party dealings, NALI/NALE, arm's-length requirements.

Why it fits: this is the core of Alfa Focus's compliance and reporting service line and the single most repeated question type a B2B SMSF administrator gets asked.

Question themes: is a specific arrangement allowed, what is the limit, what happens if the rule is breached.

Types: C1 (what is the in-house asset limit), C4 (does this specific arrangement breach it), C7 (near-miss terms like "in-house asset" vs "related party" used interchangeably).

## 2. Property in super and borrowing (LRBA)

What it covers: limited recourse borrowing arrangements, conditions for a fund buying property with debt, related-party leasing of fund-owned property.

Why it fits: named directly in the client brief as one of Alfa Focus's strategic advice areas ("property in super, specifically borrowing to acquire property").

Question themes: what conditions an LRBA must satisfy, whether a specific property purchase is permitted, related-party rent at market rate.

Types: C1 (what is an LRBA), C4 (a scenario: fund wants to buy commercial property with a loan - what must be checked), C6 (refuse to recommend whether the client should do the purchase - CH-16).

## 3. Contribution caps, thresholds, and eligibility

What it covers: concessional and non-concessional caps, bring-forward arrangements, work test, total super balance eligibility gates, and where a business sale intersects with super - e.g. contributing sale proceeds under the small business CGT concessions' own super contribution cap.

Why it fits: this is the highest-volume, most date-sensitive question class in the whole domain (`DOMAIN-PRIMER.md` section 2a) and the small-business-concession contribution pathway is a genuine point where SMSF and small-business tax meet, not a stretch into general tax.

Question themes: current-year figures, past-year figures, eligibility for a cap or concession given a scenario.

Types: C1 (current cap), C2 (date-sensitive - prior year cap, the domain's signature failure mode), C3 (stale premise - user quotes an old cap as current).

## 4. Pension phase, condition of release, and transfer balance cap

What it covers: preservation age, conditions of release, general and personal transfer balance cap, TBAR reporting.

Why it fits: directly in the worked example used in the benchmark design (`EVALUATION.md` section 3, C4 question 14, "a 63-year-old member ... start an account-based pension") and a good test of the assistant's most important refusal behaviour - stating the general cap while declining to state a member's personal cap, which depends on fund-specific TBAR history it does not hold.

Question themes: eligibility to start a pension, cap figures, why a personal cap can't be answered.

Types: C1 (general cap), C4 (multi-hop pension eligibility scenario), C6 (must-refuse - personal, member-specific TBC).

## 5. Cross-border and residency status of a fund

What it covers: the SMSF residency test (central management and control, active member test) - what happens to a fund's compliance status if a trustee or member moves or works overseas.

Why it fits: this maps directly onto the card's "Cross-Border Transactions and Residency Status" example, and unlike most cross-border tax topics it is a core SMSF compliance question, not a detour into international tax - a fund that fails the residency test can be made non-complying (`DOMAIN-PRIMER.md` section 1).

Question themes: does a specific overseas move break fund residency, what the consequence of losing complying status is.

Types: C1 (what is the residency test), C4 (scenario - trustee relocates overseas for two years, is the fund still resident).

## 6. Division 296 and large-balance reporting

What it covers: the new tax on total super balances above $3m from 1 July 2026, what SMSF trustees must report and by when.

Why it fits: named in the domain primer as the single largest live regulatory change and a strong source of "keeping up with change" questions (`REQUIREMENTS.md` UC-5).

Question themes: commencement date, thresholds, reporting obligations, how it differs from Division 293 (a well-documented confusion risk).

Types: C1 (thresholds and date), C2 (date-sensitive), C7 (adversarial - conflating Division 296 with Division 293).

## 7. SMSF establishment and annual compliance cycle

What it covers: trustee/member structure (up to six members, all also trustees), trust deed requirements, the annual return (SAR), and the independent audit requirement.

Why it fits: covers Alfa Focus's establishment and compliance/reporting service lines end to end, and is the natural home for "how does the firm handle X" firm-procedure questions once Corpus B exists.

Question themes: structural eligibility rules, who can audit a fund, what the annual compliance cycle involves, firm-specific process (e.g. pre-audit checklist).

Types: C1 (member limit, auditor independence), C5 (firm-procedure - requires Corpus B, currently the biggest delivery risk per `CLIENT-BRIEF.md` section 3).

---

## Noted but out of scope for now

These appeared in the card's example list but do not fit a firm the client brief describes as SMSF-only. Confirm against client meeting question 1 (`REQUIREMENTS.md` section 9) before treating them as use cases:

- **Inheritance / estate planning** - only relevant to the extent it touches death benefits paid from an SMSF (a real SMSF topic - binding death benefit nominations, tax on death benefits to non-dependants). Worth adding as a use case if the client confirms this comes up; not added here to avoid inventing a use case with no evidence behind it.
- **Fringe Benefits Tax** - an employer-side tax with no direct SMSF angle. Would only be in scope if Alfa Focus runs a general tax/business-services book alongside SMSF work.
- **Division 7A and corporate distributions** - a private-company tax issue, not an SMSF one. Same condition as FBT above.
- **General business transactions** - too broad to be a use case as stated; would need a specific angle (e.g. a business owner's SMSF implications) to be testable.

## Handoff Notes

Done: Identified 7 SMSF-specific accounting use cases for the chatbot, grounded in Alfa Focus's actual services rather than generic accounting topics, each with question themes and mapped to the existing C1-C7 question-type taxonomy from EVALUATION.md.

Deliverable: `docs/USE-CASES.md` (merged to `main`)

Note for next role: Four of the card's example themes (inheritance, FBT, Division 7A, general business transactions) are flagged out of scope pending client confirmation of whether Alfa Focus also runs a general tax book - see the last section. Please review the 7 use cases against the client meeting notes once available, and use these as the basis for the next Q&A batch (should give at least 5 definitive pairs per use case).
