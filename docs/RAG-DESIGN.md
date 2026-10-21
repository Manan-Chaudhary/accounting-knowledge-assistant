# RAG Design

> **Status: design document, only partly built.** Read the README for what exists. Built: hybrid retrieval (BGE-M3 dense plus Postgres full-text, reciprocal rank fusion, cross-encoder rerank), a grounding gate, `[n]` citation checking, and the system prompt. Not built: the two-corpus split in the schema (no `corpus` column and no Corpus B documents), the section 4 schema (the real tables are in [`DATABASE.md`](DATABASE.md)), temporal filtering and supersession, corpus routing, the agentic multi-hop loop, the query-planning step, the link checker and scheduled re-crawl, and the change digest. Sections 4 to 7 describe the intended design; where they differ from the code, the code and [`DATABASE.md`](DATABASE.md) are right. `[ASSUMED]`: the client never confirmed that Corpus B exists or can be created.

## 1. What we are building, and what we are not

**Building:** an internal, citation-first question-answering assistant for Alfa Focus staff. Two kinds of question - what does the law require, and how does this firm do it - answered separately and labelled as such, with every claim traceable to a source a human can open.

**Not building:** anything that gives advice to a trustee or a client directly, computes a member's personal tax position, or produces a deliverable that leaves the firm without a registered agent reviewing it. Those boundaries are professional-obligation driven, not scope-cutting. State them in the proposal as design principles; they read as competence, not as limitation.

## 2. The central design decision: two corpora, never blended

| | Corpus A - Authority | Corpus B - Firm practice |
|---|---|---|
| Content | Legislation, ATO rulings and guidance, TPB, APESB, AASB, professional bodies | SOPs, checklists, engagement templates, software runbooks, precedent file notes, internal policy |
| Provenance | Public URL, resolvable, quotable | Internal document + version + owner |
| Authority | Binding or regulator-stated | The firm's chosen method - a convention, not a rule |
| Volatility | Changes on statutory dates, mostly 1 July | Changes when a partner decides |
| Failure mode if wrong | Regulatory exposure | Inconsistent service |
| Sensitivity | Public | Confidential, must not leave the boundary |

**The rule:** an answer may draw on both, but every claim is attributed to one, and the two are visually separated in the response. Never a sentence like "you must lodge by the 15th" when the law says one thing and the firm's internal deadline says another.

This is the design idea to lead with in the proposal. It is specific to a regulated professional client, it shows we understood the domain rather than the technology, and it is the thing a generic RAG demo does not do.

In the schema this is one column, `corpus`, on `documents` and `document_chunks`. In the prompt it is the section split in [`PROMPTS.md`](PROMPTS.md). In evaluation it is the `corpus_attribution` scorer. One decision, enforced in three places.

**The delivery risk it exposes:** Corpus B may not exist in written form. A ~10-person practice keeps its method in senior heads. Budget for *creating* Corpus B - structured interviews with the SMSF accountants and the customer service manager, written up as documents the firm owns afterwards. Frame this to the client as a deliverable in its own right, because it is: even if the software were deleted, a documented firm method is worth having. See [`CLIENT-MEETING-QUESTIONS.md`](CLIENT-MEETING-QUESTIONS.md) Q3.

## 3. Where each piece lives

This table is the contract between the design and the code. The "Currently" column was updated to the code on `main`.

| Module | Currently | What it owns |
|---|---|---|
| `app/routes/upload.py` | Implemented | `POST /api/upload`, document list, status, delete, retry. Stores the file, inserts the row, triggers n8n |
| `app/services/storage_service.py` | Implemented (Supabase client helper) | Raw file into Supabase Storage |
| `app/services/document_service.py` | Implemented | Document lifecycle (`process_document`): extract, chunk, embed, store. No metadata extraction beyond `section_heading` |
| `app/rag/embedder.py` | Implemented | BGE-M3 via Hugging Face `InferenceClient`, used for both ingest and query |
| `app/rag/retriever.py` | Implemented (hybrid + RRF + rerank) | No temporal filter or corpus routing. See section 5 |
| `app/rag/reranker.py`, `app/rag/grounding.py` | Implemented | Cross-encoder rerank; grounding gate and citation verification |
| `app/rag/generator.py` | Implemented | Prompt assembly from [`PROMPTS.md`](PROMPTS.md), LiteLLM call (streaming and not). Citation checking is in `grounding.py`, not here |
| `app/chainlit/chainlit_app.py` | Implemented | Chainlit app for history persistence and auth; the main chat UI is the React `/assistant` page using `/api/chat/stream` |
| `app/routes/testing.py` | Implemented | The evaluation surface (`/testing`, team role). See [`EVALUATION.md`](EVALUATION.md) |
| `app/db/models.py`, `app/db/schema.sql` | Implemented, mirrored | Real schema in [`DATABASE.md`](DATABASE.md), not section 4 |
| `app/config.py` | Implemented | Every env var in one place |

Two notes (updated):

- **The `Dockerfile` exists** (React build stage plus `python:3.11-slim`) and `docker-compose.yml` runs the app, LiteLLM and n8n. There is no hosting: no Render or other deployment was set up.
- **`.github/workflows/deploy.yml` does not deploy.** It is a commit-message check named `Commit Message Check`, and was not renamed. CI (`ci.yml`) only installs dependencies and compiles; its pytest step is commented out.

## 4. The chunk contract

*Design, not what is built.* The real schema has no `corpus`, `tier`, `effective_from`, `income_years`, `tsv` or `superseded_by` columns, uses 1024-dimension vectors (BGE-M3, not 1536), integer ids, and an IVFFlat index; keyword search computes `to_tsvector` at query time. See [`DATABASE.md`](DATABASE.md).

The retrieval quality of this system is decided here, not in the model choice. This is the proposed content of `app/db/schema.sql`, and `app/db/models.py` mirrors it.

```sql
create extension if not exists vector;

create table documents (
    id              uuid primary key default gen_random_uuid(),
    corpus          char(1)      not null check (corpus in ('A','B')),
    tier            smallint     not null check (tier between 1 and 4),
    title           text         not null,
    publisher       text,
    source_url      text,          -- required for corpus A, null for corpus B
    internal_ref    text,          -- e.g. 'SOP-SMSF-Audit-Prep', null for corpus A
    version         text,
    doc_type        text         not null,  -- legislation|ruling|determination|guidance|standard|sop|checklist|filenote
    effective_from  date         not null,
    effective_to    date,          -- null = currently in force
    superseded_by   uuid references documents(id),
    retrieved_at    timestamptz  not null default now(),
    url_last_ok     timestamptz,   -- set by the link checker
    created_at      timestamptz  not null default now()
);

create table document_chunks (
    id            uuid primary key default gen_random_uuid(),
    document_id   uuid not null references documents(id) on delete cascade,
    chunk_index   int  not null,
    section_path  text,            -- 'Super > SMSF > Newsroom' or 's 62(1)(b)'
    content       text not null,
    income_years  text[] not null default '{}',   -- {'2026-27'} - drives the temporal filter
    embedding     vector(1536),
    tsv           tsvector generated always as (to_tsvector('english', content)) stored,
    unique (document_id, chunk_index)
);

create index on document_chunks using hnsw (embedding vector_cosine_ops);
create index on document_chunks using gin (tsv);
create index on documents (corpus, effective_from, effective_to);
```

Four things earn their place:

- **`effective_from` / `effective_to` / `income_years`.** Non-negotiable. Without these the system will confidently quote last year's caps, which is the single most likely way this project fails a client demo.
- **`superseded_by`.** Lets the assistant say "the rule you are describing applied until 30 June 2026; here is what replaced it" instead of silently returning stale text. This turns the hardest failure mode into a feature.
- **`tier`.** Drives ranking and the wording of the answer.
- **`tsv` as a generated column.** The lexical half of hybrid retrieval, maintained by Postgres with no application code and no second system to run. This is why pgvector-on-Supabase was the right call - one query can filter on dates, match keywords, and rank by vector distance together.

**Chunking is structure-aware, not fixed-size** (built: `app/rag/chunker.py`, headings, numbered clauses and tables, 1200 characters with 150 overlap; see [`CHUNKING-DESIGN.md`](CHUNKING-DESIGN.md)). The detail below is the original design. Legislation splits on section and subsection; ATO pages on heading; checklists on the individual step, because a step is the unit a user acts on. Keep `document_id` so `generator.py` can pull surrounding context when a chunk is ambiguous. Fixed 512-token windows will cut a subsection in half and destroy exactly the precision this domain needs.

**`source_url` is validated at ingest.** A citation that 404s is worse than no citation, because it looks authoritative. Re-check on a schedule, write `url_last_ok`, and alarm on breakage.

**Refresh:** scheduled re-crawl of the ATO SMSF Newsroom and the tracked guidance pages. On change, insert a new `documents` row, set `effective_to` and `superseded_by` on the old one, and **never delete** - the history is what lets the assistant answer questions about prior years. Surface a weekly "what changed" digest to the firm. That digest may end up being the feature they value most, because it addresses the "ever-evolving practices" pain without anyone having to ask a question first.

## 5. Retrieval - what goes in `retriever.py`

*As built:* dense top 20 plus keyword top 20, fused with RRF (k = 60), best 20 reranked by `cross-encoder/ms-marco-MiniLM-L-6-v2`, top 5 returned (the evaluation harness uses top 6). The temporal filter, corpus routing and agentic loop below are not built.

**Hybrid, always.** Dense embeddings plus Postgres full-text, fused with reciprocal rank fusion, then a cross-encoder rerank over the top ~50 down to a final ~8. The lexical channel is not optional here: "Division 296" and "Division 293" are different taxes with near-identical embeddings, and citation identifiers like `TR 2010/1` or `s 62` are exact tokens. Hybrid-plus-rerank is also the consensus best quality-to-cost point in current practice, so this is a defensible default rather than an exotic choice.

**Temporal filtering before ranking, not after.** Resolve the query's income year first - explicit if the user gave one, otherwise the current year - then filter candidates with `income_years && ARRAY[$year]` or the `effective_from`/`effective_to` window. A same-similarity chunk from the wrong year should never compete for a slot.

**Corpus routing.** Classify the query as authority-seeking, practice-seeking, or both, and retrieve accordingly. "What does the law say" and "what do we do" want different sources, and retrieving both for every query wastes context and invites blending.

**Agentic loop, bounded.** For multi-hop questions - which is most real questions - let the pipeline plan sub-queries, retrieve, assess sufficiency, and re-retrieve, with a hard cap of 3 iterations and a fallback to escalation. Do not make every query agentic; simple lookups take the fast path. Route on query complexity.

Worth knowing when things go wrong: retrieval, not generation, is the failure point in the large majority of RAG failures. Instrument and evaluate it separately, and resist the urge to fix a bad answer by editing the prompt.

## 6. Generation and the answer contract

Every response conforms to a fixed shape, enforced with structured output rather than hoped for in a prompt. The full prompt text lives in [`PROMPTS.md`](PROMPTS.md); the shape is:

```
ANSWER               - direct, scoped to an income year where the claim is date-dependent
BASIS IN LAW         - Corpus A claims with inline [n] citations
HOW ALFA FOCUS DOES THIS - Corpus B steps, omitted entirely if no Corpus B hit
CONFIDENCE AND LIMITS - what this does not cover, what a human must check, any tier 3-4 source named
SOURCES              - [n] title, publisher, effective from, URL
```

Six behavioural rules, each of which becomes an evaluation check in [`EVALUATION.md`](EVALUATION.md):

1. **No citation, no claim.** If retrieval returns nothing above threshold, the answer is an escalation, not a guess. A confident unsourced answer is the worst possible output for this client.
2. **Never state a member-specific figure.** Personal TBC, a member's TSB, a specific fund's position - these depend on data the assistant does not have and must not guess.
3. **Date-scope every volatile claim.** "For 2026-27, ..." Not "the cap is ...".
4. **Flag supersession.** If the question embeds a stale premise, correct it before answering.
5. **Refuse personal financial advice.** The firm is a tax agent, not necessarily licensed for personal financial product advice.
6. **Attribute corpus per claim.** Never present a firm convention as a legal requirement.

**Citation validation runs after generation, in code, before the response is returned.** Every `[n]` must map to a chunk that was actually retrieved, and every URL must be live. This is a deterministic check, not a judgement, and it is the last line of defence against a fabricated ruling.

## 7. Request path

*Design.* As built, `/api/chat/stream` runs `retrieve` (hybrid + rerank), then `evaluate_grounding_gate`, then `generate_response_stream`, then `verify_and_clean_citations`, and returns sources to the React page. There is no query plan, sufficiency loop or URL liveness check, and sign-in is email and password, not SSO.

```
accountant -> /chat (Chainlit, SSO)
    |
    chainlit_app.on_message
    |
    generator.build_query_plan
      - resolve income year
      - expand acronyms (TBAR, LRBA, NALI)
      - classify corpus + complexity
    |
    retriever.search
      - hybrid: embedding (pgvector) + tsv (full-text), RRF fused
      - temporal filter applied pre-rank
      - corpus + ACL filter
      - cross-encoder rerank -> top 8
    |
    sufficiency check --insufficient--> re-plan (max 3) --> escalate
    |
    generator.generate  (answer contract, structured output)
    |
    generator.validate_citations  (deterministic: [n] resolves, URL live)
    |
    response + trace -> DB  ->  /testing reads the same traces
```

Everything inside this path is subject to the confidentiality constraint in [`DOMAIN-PRIMER.md`](DOMAIN-PRIMER.md) section 5.

## 8. Decisions still open

Not deferred - defaulted, with the trigger to revisit named.

| Decision | Default | Revisit if |
|---|---|---|
| Embedding model | A current general model, measured against a domain alternative on our own retrieval set | Domain eval says otherwise. Do not assume; measure. `embedder.py` is one file precisely so this is swappable |
| Generation model | A current frontier model with strong instruction-following | Cost or data-residency rules it out. **Must have contractual no-training terms** - this is a proposal-level commitment, not a code choice |
| Reranker | Cross-encoder | Latency budget is blown |
| Auth | Built as email and password sessions owned by FastAPI, shared with Chainlit; no SSO | Client mandates otherwise |
| MLflow | Not added; the custom harness in `app/evaluation/harness.py` is used instead. See [`EVALUATION.md`](EVALUATION.md) | The unit mandates a different harness |

## 9. Phasing

*Plan, not history.* In practice the team built a Corpus A slice across 73 documents, the hybrid retriever, the harness and the chat and document UIs. Phases 2 to 4 (Corpus B, agentic multi-hop and freshness, hardening) did not happen.

Sized for a capstone semester, ordered so each phase is independently demonstrable and maps to branches under the naming rules in [`GIT-WORKFLOW.md`](GIT-WORKFLOW.md).

- **Phase 0 - Ground truth.** Client meeting. Confirm the scope of work (a generalist firm with an SMSF line), the software, the real question distribution. Get 30-50 real questions from the customer service manager. Nothing is built until this exists.
- **Phase 1 - Corpus A vertical slice.** One narrow topic - contribution caps and the transfer balance cap - ingested with full temporal metadata. `schema.sql`, `embedder`, hybrid `retriever`, answer contract in `generator`, real answers in `/chat`. Benchmark v1 and the eval harness stand up **in this phase**, not later. A working eval on a narrow slice beats a broad demo with no measurement. Also (planned): get a hosted deployment working. This did not happen; the Dockerfile exists but nothing is hosted.
- **Phase 2 - Corpus B.** Interviews, write up firm procedures, ingest through `/upload` with ACLs. Two-corpus answer contract live. This is where the client sees something they cannot buy off the shelf.
- **Phase 3 - Agentic multi-hop and freshness.** Query planning loop, scheduled re-crawl, supersession handling, the weekly change digest.
- **Phase 4 - Hardening.** Judge alignment against accountant labels, CI gates, monitoring, handover documentation for a firm with no IT staff.

If time compresses, cut Phase 3 and keep Phase 2. The two-corpus story is the differentiator; multi-hop is table stakes that can be demonstrated on a narrow topic.

## 10. Known risks

| Risk | Why it bites | Mitigation |
|---|---|---|
| Corpus B does not exist in writing | Half the value proposition disappears | Named as a scoped deliverable with client time committed, at the first meeting |
| Client unavailable or slow | Small firms are busy in the second half of the year | Build on Corpus A, which is entirely public. The system must be demonstrable with zero client input |
| Golden answers need expertise we lack | Benchmarks become guesses | Three-route ground truth strategy in [`EVALUATION.md`](EVALUATION.md); behavioural questions need no tax expertise |
| Confidentiality blocks the intended model | Rework late | Settle the data-handling question in the proposal, before building |
| Stale answers in a demo | Fatal credibility loss with this audience | Temporal metadata from day one; supersession is a first-class feature, not a fix |
| Scope drift toward "chatbot for clients" | Regulatory exposure, and a worse product | The boundary in section 1 is written into the proposal |
| No deployment; misnamed `deploy.yml` | Deployment is assumed working and is not | `deploy.yml` is still a commit-message check and nothing is hosted; the next team must decide on hosting |
