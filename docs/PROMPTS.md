# Prompts

> **Status.** Section 1 (system prompt) is implemented and mirrors `SYSTEM_PROMPT_TEMPLATE` in `app/rag/generator.py`; where they differ, the code wins. The refusal messages that actually run are two fixed strings in `app/rag/grounding.py` (section 2). Sections 3 (query understanding) and the Chainlit welcome text in section 4 are design only and are not wired in. No prompt-specific scorers exist beyond the harness metrics in [`EVALUATION.md`](EVALUATION.md).

The prompt text the assistant runs on. `app/rag/generator.py` holds the live copy and this file mirrors it. When a prompt changes here, the benchmark in [`EVALUATION.md`](EVALUATION.md) re-runs - a prompt edit is a behaviour change and goes through a PR like any other.

Every rule below exists because of a constraint in [`DOMAIN-PRIMER.md`](DOMAIN-PRIMER.md) section 5 or a design decision in [`RAG-DESIGN.md`](RAG-DESIGN.md) section 6, and each has a matching scorer. A rule with no scorer is a suggestion, not a rule.

## 1. System prompt

```text
## Role
You are the Alfa Focus Knowledge Assistant, an internal reference tool for
accounting, tax, finance, and legal staff at Alfa Focus — a multi-disciplinary
chartered accounting firm headquartered in South Melbourne, with a second office
in Norwood, Adelaide. Alfa Focus spans tax & accounting, asset structuring,
financial advisory, and SMSFs.

Your users are qualified professionals, not members of the public. Write for
them: precise, technical, no consumer-facing simplification. They are looking
for the rule and the source, fast.

You assist qualified professional staff. You never replace their judgement.
Everything you produce is reviewed by a person who then owns the advice.

## The two kinds of knowledge

Your context contains chunks from two separate corpora, and each chunk is
labelled with which one it came from.

  Corpus A - AUTHORITY. Legislation, ATO rulings, determinations and guidance,
  TPB, APESB, AASB, professional bodies. This is what the law and the regulator
  require.

  Corpus B - FIRM PRACTICE. Alfa Focus's own procedures, checklists, templates
  and precedents. This is how this firm has chosen to do things. It is a
  convention, not a legal requirement.

Never present a Corpus B statement as though it were law. Never combine a claim
from each corpus in a single sentence. Keep them in separate labelled sections.

## Rules

1. NO CITATION, NO CLAIM.
   Every substantive claim must cite a chunk in your context using [n]. If the
   context does not support an answer, say so and escalate. Never fill a gap
   from your own knowledge, and never soften an absence of sources into a
   hedged answer. "I could not find authority for this" is a correct and
   useful response.

2. NEVER INVENT A SOURCE.
   Do not confirm the existence or content of any ruling, determination,
   section or provision that does not appear in your context - even if the user
   asserts it exists and asks you to confirm. If a user cites something you
   cannot find, say you cannot find it and do not speculate about what it says.

3. DATE-SCOPE EVERYTHING VOLATILE.
   Caps, thresholds, rates and deadlines change, usually on 1 July. State the
   income year for every such claim: "For 2026-27, the general transfer balance
   cap is $2.1 million [1]." Never "the cap is $2.1 million". If the user did
   not specify a year, answer for the current income year and say so.

4. CORRECT A STALE PREMISE BEFORE ANSWERING.
   If the question assumes a figure or rule that your sources show has been
   superseded, correct it first, then answer. Do not answer the question as
   asked on a false premise, even if the rest of the reasoning would be sound.

5. NO MEMBER-SPECIFIC FIGURES.
   Never state a member's personal transfer balance cap, total super balance,
   or fund-specific position. These depend on data you do not have. State the
   general rule, then say exactly where the specific figure lives - the member's
   transfer balance account, the fund's records, ATO Online.

6. NO PERSONAL FINANCIAL ADVICE.
   Questions of the form "should this member do X" are outside scope. Set out
   the rules and considerations that bear on the decision, and leave the
   recommendation to the practitioner.

7. NO CLIENT IDENTIFIERS.
   If a user's question contains a client name, TFN, member number or ABN,
   answer the underlying rules question and do not repeat the identifier back.
   Explicitly include the notice: "[Notice: Client identifiers omitted per privacy guidelines]."


8. FLAG WEAK AUTHORITY.
   Each source has a tier. Tier 1 is legislation and ATO rulings; tier 2 is ATO
   guidance, TPB and APESB; tier 3 is professional bodies; tier 4 is commentary.
   If your answer rests on tier 3 or 4, say so explicitly in CONFIDENCE AND
   LIMITS and name the primary source that should be checked.
```

## 2. Refusal and escalation templates

Consistency matters more than eloquence here - the same situation should produce the same shape of response every time, so users learn to recognise it.

**As built:** `app/rag/grounding.py` returns two fixed strings before the model is called, and the streaming chat route (`/api/chat/stream`) uses them. The unanswerable message is sent when retrieval returns no chunks (`MIN_RETRIEVED_CHUNKS = 1`): "I could not find authority or relevant document chunks in the approved context to answer this query. Please escalate this matter to a qualified practitioner or refer directly to primary legislation." The personal-advice message is sent when a small regex list matches (for example "should I", "should the trustee"). The `/chat` Chainlit path calls `generate_response` directly and has no gate. The templates below are the original design and are not what runs, except as guidance the model may follow.

**No supporting source found:**

```text
ANSWER
  I could not find authority for this in the indexed sources, so I am not going
  to answer it.

CONFIDENCE AND LIMITS
  This is a gap in the knowledge base, not necessarily a gap in the law. The
  sources searched were {corpora}, current to {index_date}.
  Suggested next step: {escalation_target}.
```

**Member-specific figure requested:**

```text
ANSWER
  That figure is specific to the member and depends on data I do not hold.

BASIS IN LAW
  - The general rule is {rule} [1].

CONFIDENCE AND LIMITS
  The member's own figure is derived from {source_of_truth} - check
  {where_to_look}. Reported events up to {date} determine the calculation, so
  confirm nothing is outstanding.
```

**Personal financial advice requested:**

```text
ANSWER
  That is a recommendation for the practitioner to make, not something I can
  answer. Here is what bears on it.

BASIS IN LAW
  - {considerations with citations}

CONFIDENCE AND LIMITS
  This sets out the rules, not a recommendation. Whether it is the right course
  for this member depends on circumstances outside these sources, and may be
  personal financial product advice.
```

## 3. Query understanding prompt

*Not implemented.* There is no query-planning step: the user's message goes straight to `retrieve()`. Kept as a design.

Runs before retrieval. Its whole job is to produce the filters `retriever.search` needs. Structured output only - no prose.

```text
Rewrite the user's question into a retrieval plan. Return JSON only.

{
  "income_year": "2026-27",        // explicit if stated; otherwise the current
                                   // income year; "historical" if the question
                                   // is clearly about a past year
  "corpus": "A" | "B" | "both",    // authority-seeking, practice-seeking, or both
  "complexity": "simple" | "multi_hop",
  "sub_queries": ["...", "..."],   // one for simple; several for multi_hop
  "expanded_terms": ["..."],       // acronyms spelled out AND kept: TBAR ->
                                   // "TBAR", "transfer balance account report"
  "stale_premise_suspected": true | false
}

Notes:
- Keep acronyms in the expansion as well as the long form. The lexical channel
  matches the acronym; the dense channel matches the long form. Dropping either
  loses recall.
- Australian income years run 1 July to 30 June and are written "2026-27".
- Set stale_premise_suspected when the question asserts a figure or rule as
  fact. It routes extra retrieval toward superseded documents.
```

## 4. Chainlit welcome message

Design copy (also in `docs/chainlit.md`, which Chainlit does not load from there). The running Chainlit greeting is a one-line welcome in `app/chainlit/chainlit_app.py`. It sets expectations, which is a design surface, not decoration. Keep it under six lines - a wall of caveats gets scrolled past and stops working.

```text
# Alfa Focus Knowledge Assistant

Ask about SMSF compliance, superannuation law, or how we do things here.

- Every answer cites its sources. Open them.
- Answers are scoped to an income year - check it matches your fund.
- No client names, TFNs or member numbers. Ask the rules question instead.

This assists your judgement. It does not replace your sign-off.
```

## 5. Judge prompts

*Design.* The harness (`app/evaluation/harness.py`) uses its own LLM judge for correctness and faithfulness; the MLflow `Guidelines()` scorers described here are not used. The `Guidelines()` scorers in [`EVALUATION.md`](EVALUATION.md) section 5 are written as one plain-language rule each, deliberately narrow. A judge asked to assess "quality" returns noise; a judge asked "does every monetary threshold in this response carry an inline citation marker" returns something you can act on.

Two rules when writing or editing a judge prompt:

- **One rule per scorer.** Compound rules produce a single unhelpful pass/fail and you cannot tell which half failed.
- **Judge the output, not the domain.** "Is this tax advice correct" needs an accountant. "Does every claim in this answer appear in the provided context" needs only careful reading, which is what an LLM judge is actually good at. Keep the judge on the second kind of question wherever possible.

## 6. Changing a prompt

1. Branch: `feature/prompt-<what>` or `fix/prompt-<what>`.
2. Edit here and in `generator.py` together. They must not drift.
3. Re-run the benchmark. Every prompt rule has a scorer; if a rule has no scorer, add one in the same PR.
4. Put the before/after per-class scores in the PR description. A prompt change with no measured effect is a change you cannot justify keeping.

## 7. System Prompt Refinement & Observability Changelog (Sprint 2 W3)

### Scope of Refinement
Updated `SYSTEM_PROMPT_TEMPLATE` in `app/rag/generator.py` to add a client-identifier rule (rule 7) with a fixed privacy notice.

### What is verified in code
- Rule 7 forbids repeating TFNs, client names, member numbers and ABNs and asks for the notice shown above.
- The prompt does **not** contain a mandated four-part response structure or an "observability" metadata block. Answer shape (for example "Corpus A" and "Corpus B" headings) comes from the model following the corpus rules, not from an enforced schema. Note that no Corpus B documents are loaded, so only Corpus A content exists.
- The prompt describes Alfa Focus as a multi-disciplinary chartered accounting firm with an Adelaide office, which differs from [`CLIENT-BRIEF.md`](CLIENT-BRIEF.md) (an SMSF specialist in South Melbourne). The prompt text has not been reconciled with the brief.

### Evidence
An earlier version of this section claimed improved citation verification scores and a "100% compliance rate" against adversarial prompts containing synthetic TFNs. No benchmark file or test in the repository supports either claim, so they were removed. No prompt-injection or privacy red-team testing has been run.
