# Alfa Focus Knowledge Assistant

An internal, citation-first knowledge assistant for **Alfa Focus**, a generalist tax and accounting firm in South Melbourne. Built by Team 83 as the RMIT COSC2408 Programming Project 1 capstone.

The problem: Australian tax and superannuation rules change constantly - 1 July 2026 alone brought Division 296, payday super, and an indexed transfer balance cap - and firm-specific procedure lives in senior heads rather than in writing. Accountants lose time re-deriving answers, and two staff can give a referring planner two different answers.

The assistant answers from an approved library of documents (ATO guidance, legislation, TPB and APESB standards) and shows numbered sources with every answer. It assists a registered tax agent; it never signs off.

> **Status: prototype, handed over locally.** The system runs on Docker Compose and is not deployed. The client was never met, so the question set and document list are assumptions (see [`docs/CLIENT-MEETING-QUESTIONS.md`](docs/CLIENT-MEETING-QUESTIONS.md)). It has not been tested with real Alfa Focus users, and security hardening was descoped. Everything in [`docs/CLIENT-BRIEF.md`](docs/CLIENT-BRIEF.md) is open-source research carrying explicit confidence markers. Do not quote a `MEDIUM` or `LOW` fact to the client as settled.

## What it does

- **Chat** (`/assistant`): streamed answers grounded in retrieved documents, numbered sources, saved chat history in a sidebar, chat delete, and a model selector.
- **Documents** (`/documents`): upload a document, track its ingestion status (`pending`, `processing`, `ready`, `failed`), retry a failed one, delete a document.
- **Ingestion**: an upload is stored in Supabase Storage, then an n8n workflow calls the FastAPI `process-document` endpoint, which parses, chunks, embeds (BGE-M3) and stores the chunks.
- **Retrieval**: hybrid search (pgvector dense + Postgres full-text), fused by reciprocal rank fusion, then reranked with a cross-encoder.
- **Grounding**: a gate refuses to answer when retrieval finds no usable source, and citations in the answer are checked against the retrieved sources.
- **Sign-in**: FastAPI owns a signed session cookie that Chainlit reuses. Roles are `staff`, `admin` and `team`.
- **Evaluation** (`/testing`, `team` role only): runs the 50-question benchmark in `benchmarks/questions.jsonl` against a chosen model and scores retrieval, citations and refusals.
- **Swappable LLM**: all generation goes through a LiteLLM proxy with fallbacks (`litellm/config.yaml`).

Not delivered, so don't assume they work: chat rename, document list filters, feedback buttons, copy-with-citations, document versioning, OCR for scanned PDFs, an unanswered-questions dashboard, and security hardening.

## Documentation

The README and `docs/` describe the system as built. Files marked *design* are the original requirements and research; read the code and the handover document where they differ.

| Doc | What it answers |
|---|---|
| [`docs/CLIENT-BRIEF.md`](docs/CLIENT-BRIEF.md) | Who Alfa Focus is: a generalist tax and accounting firm, with SMSF administration as one of its service lines |
| [`docs/DOMAIN-PRIMER.md`](docs/DOMAIN-PRIMER.md) | Australian SMSF practice for a team with no accounting background; the professional-obligation constraints behind the design |
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | *Design.* Numbered, testable requirements: chatbot behaviour, file upload, data handling, edge cases |
| [`docs/RAG-DESIGN.md`](docs/RAG-DESIGN.md) | *Design.* The two-corpus split, chunk schema, hybrid and temporal retrieval |
| [`docs/CHUNKING-DESIGN.md`](docs/CHUNKING-DESIGN.md) | How documents are split into chunks |
| [`docs/PROMPTS.md`](docs/PROMPTS.md) | The system prompt and refusal templates behind `app/rag/generator.py` |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Benchmark taxonomy, metrics, and results of the model comparison |
| [`docs/DOCUMENT-CORPUS.md`](docs/DOCUMENT-CORPUS.md) | The 73-document corpus and how it was built |
| [`docs/DATABASE.md`](docs/DATABASE.md) | PostgreSQL + pgvector setup, BGE-M3 embeddings, schema reference |
| [`docs/GIT-WORKFLOW.md`](docs/GIT-WORKFLOW.md) | Branch naming, commit format, PR and CI requirements |
| [`docs/UAT-SCRIPT.md`](docs/UAT-SCRIPT.md) | User acceptance test script (written, not run) |
| [`docs/CLIENT-MEETING-QUESTIONS.md`](docs/CLIENT-MEETING-QUESTIONS.md) | The 14 questions the next team should put to Alfa Focus first |

## Design principles

1. **No citation, no claim.** If retrieval finds nothing, the assistant refuses rather than guesses.
2. **Every volatile claim is scoped to an income year.**
3. **Law and firm practice are never blended in one sentence.**
4. **No client identifiers, no member-specific figures.** The assistant answers rules questions. Nothing automated enforces this yet: it relies on the system prompt and on users not entering client data.
5. **Deterministic checks beat judged ones.** Citation validity is checked in code, not by an LLM.

## Architecture

```
Browser (React SPA)
   |  same origin, signed session cookie
   v
FastAPI (app/main.py, port 8000)
   |-- /api/auth, /api/chat, /api/upload, /api/documents, /api/testing  (routers)
   |-- /chat            Chainlit app mounted into FastAPI (history persistence, auth header)
   |-- everything else  built React SPA (frontend/dist), catch-all, mounted last
   |
   |-- RAG pipeline (app/rag): embedder -> retriever (hybrid + rerank) -> grounding gate -> generator
   |        |-> LiteLLM proxy (port 4000) -> Gemini / Groq / OpenRouter
   |        |-> Hugging Face Inference API (BGE-M3 embeddings)
   |-- Supabase: Postgres + pgvector (documents, chunks, users, chat threads) and Storage (raw files)
   v
n8n (port 5678): upload webhook -> POST /api/n8n/process-document/{id} (shared-secret header)
```

## Project structure

```
app/
  main.py                 Entry point. Auth middleware, routers, Chainlit mount, SPA catch-all (last)
  config.py               All env vars in one place
  auth/                   Session cookie, password hashing, Chainlit header-auth bridge, role checks
  routes/
    auth.py               /api/auth/login, /logout, /me
    chat_history.py       /api/chat: threads, messages, delete, /stream (SSE), non-streaming fallback
    upload.py             /api/upload, /api/documents (list, status, delete, retry)
    integration.py        /api/n8n/process-document/{id}, /api/n8n-test
    testing.py            /api/testing: start, poll and stop evaluation runs
    home.py               Retired, no longer registered
  chainlit/chainlit_app.py  Chainlit app: auth, settings, history resume
  services/               document_service.py (ingestion), storage_service.py (Supabase Storage)
  rag/
    chunker.py            Structure-aware chunking
    embedder.py           BGE-M3 via Hugging Face
    retriever.py          Dense + keyword + RRF fusion, then reranker
    reranker.py           Cross-encoder reranking (sentence-transformers)
    grounding.py          Grounding gate and citation verification
    generator.py          Prompt assembly, LLM call (streaming and not), history
  evaluation/harness.py   Benchmark runner and metrics
  db/                     SQLAlchemy models and schema.sql (kept mirrored)
frontend/                 React SPA (Vite + TypeScript): Home, Documents, Chat, Testing, Login
benchmarks/               questions.jsonl (50 cases), results/, reports/
corpus/                   73 source documents, manifest.json, sources.json
scripts/                  Corpus build, upload and validation; evaluation and latency runners; create_app_user
n8n/                      Document Ingestion.json workflow, workflows/ (connectivity test)
litellm/config.yaml       Model list, routing and fallbacks
tests/                    pytest suite (db, rag, evaluation)
docs/                     See the table above
```

Key points:
- `retriever.py` is where answer quality is won or lost. Retrieval, not generation, is where RAG systems usually fail.
- `models.py` and `schema.sql` mirror each other. Update both when the schema changes.
- Routers register before the SPA catch-all in `main.py`. Keep it that way or `/api` and `/chat` will be swallowed.

## Local setup

### Prerequisites

- Docker Desktop with Compose (the recommended path), or Python 3.13 and Node 22 for running without Docker
- A Supabase project (Postgres with the `vector` extension enabled, and a Storage bucket named `documents`). Run `app/db/schema.sql` against it; see [`docs/DATABASE.md`](docs/DATABASE.md)
- A Hugging Face token (BGE-M3 embeddings)
- At least one LLM key: Gemini, Groq or OpenRouter

### Configure

```bash
cp .env.example .env
```

Fill in every variable in `.env.example`:

| Variable | What it is |
|---|---|
| `SUPABASE_DB_URL` | Sync Postgres URL, `postgresql+psycopg2://...`. Must be psycopg2: the asyncpg URL breaks retrieval |
| `CHAINLIT_DATABASE_URL` | Async Postgres URL, `postgresql+asyncpg://...`, for Chainlit history |
| `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_BUCKET` | Supabase project URL, secret key and bucket (default `documents`) |
| `HF_TOKEN` | Hugging Face token for embeddings |
| `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY` | LLM provider keys |
| `GEMINI_MODEL`, `GROQ_MODEL` | Default provider model names |
| `LITELLM_MASTER_KEY`, `LITELLM_API_KEY` | Proxy master key, and the key the app uses to call it (the master key works) |
| `LITELLM_API_BASE` | `http://alfa_focus_litellm:4000/` in Docker |
| `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS` | Default model and fallbacks used by the app |
| `LITELLM_DATABASE_URL` | Postgres URL for the LiteLLM proxy |
| `SESSION_SECRET`, `CHAINLIT_AUTH_SECRET` | Random secrets. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `SESSION_MAX_AGE_SECONDS`, `CORS_ORIGINS` | Session lifetime (default 8 hours) and allowed origins |
| `N8N_SHARED_SECRET` | Shared secret n8n sends to FastAPI. Must equal the value of the `X-N8N-Secret` Header Auth credential in n8n |
| `N8N_WEBHOOK_URL` | Listed in `.env.example` but not read by any code. The app hardcodes `http://n8n:5678/webhook/process-document` in `app/routes/upload.py` |
| `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP` | Chunking settings (1200 and 150) |

`ENVIRONMENT` is optional and defaults to `development`. Set it to `production` to disable the Swagger docs and mark the session cookie HTTPS-only.

### Run with Docker Compose

```bash
docker compose up --build
```

This starts the app (8000), the LiteLLM proxy (4000) and n8n (5678). The Docker image builds the React frontend, so no separate frontend build is needed. Code is baked into the image: rebuild with `--build` after changes.

```bash
docker compose up -d --build   # detached
docker compose logs -f         # logs
docker compose down            # stop (do not add -v: it deletes the n8n volume)
```

### Run without Docker

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
(cd frontend && npm ci && npm run build)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

You still need LiteLLM and n8n running (`docker compose up -d litellm n8n`) for chat and ingestion. Note that n8n then reaches the app at `http://app:8000` only inside Compose; use the full Compose stack unless you are adjusting the workflow.

### First run

1. **Create a user.** No default credentials exist.
   ```bash
   python -m scripts.create_app_user --email you@example.com --password '...' --role team
   ```
   Roles: `staff`, `admin`, `team`. Only `team` sees the Testing page. Only `admin` and `staff` can delete documents (`app/auth/deps.py`), so a `team` user cannot.
2. **Import the ingestion workflow into n8n.** Open `http://localhost:5678`, complete owner setup, choose Import from File, select `n8n/Document Ingestion.json`, then attach a Header Auth credential to its HTTP Request node (name `X-N8N-Secret`, value equal to `N8N_SHARED_SECRET`; the export does not contain credentials). Save and activate the workflow. The webhook path is `process-document`; the app posts to `http://n8n:5678/webhook/process-document`.
3. **Load the corpus** (optional, needs the app and n8n running):
   ```bash
   CORPUS_UPLOAD_EMAIL=you@example.com CORPUS_UPLOAD_PASSWORD='...' python scripts/upload_corpus.py
   ```
   It uploads the 73 files and polls each until `ready` or `failed`, resuming from `corpus/upload_log.json`. Embedding quota is limited, so expect it to take a while.

### Verify it worked

| Page | URL |
|---|---|
| Sign in | `http://localhost:8000/login` |
| Home | `http://localhost:8000/home` |
| Chat | `http://localhost:8000/assistant` |
| Documents | `http://localhost:8000/documents` |
| Evaluation (`team` role) | `http://localhost:8000/testing` |
| API docs (development only) | `http://localhost:8000/docs` |
| n8n | `http://localhost:5678` |

After signing in, upload a small document, watch it reach `ready`, then ask a question it answers. The answer should stream with a numbered source.

## Testing

```bash
source .venv/bin/activate
pytest -v
```

- `tests/evaluation/`, `tests/rag/` and `tests/test_reranker.py` run without a database or API key where retrieval and generation are mocked.
- `tests/db/` needs a real `.env` with working Supabase and Hugging Face credentials.
- CI (`.github/workflows/ci.yml`) installs dependencies and runs `python -m compileall app`. It does not run pytest yet: the step is commented out.

## Running evaluations

From the UI: sign in as a `team` user and use `/testing`. From the command line, the harness (`app/evaluation/harness.py`) runs each case in `benchmarks/questions.jsonl` (50 cases) through retrieval and generation, then scores retrieval (source hit, recall@k, MRR), citations (present, valid), refusal behaviour and latency. It needs `SUPABASE_DB_URL` (the synchronous URL) plus `GEMINI_API_KEY` or `GROQ_API_KEY`.

```bash
python -m scripts.run_evaluation --model gemini/gemini-3.8-flash --judge gemini/gemini-3.8-flash --output benchmarks/results/gemini-3.8-flash.jsonl --report benchmarks/reports/gemini-3.8-flash.md
```

Compare several runs in one report:

```bash
python -m scripts.evaluation_report benchmarks/results/a.jsonl benchmarks/results/b.jsonl --output benchmarks/reports/comparison.md --title "Model comparison"
```

- `--rescore` recomputes the deterministic metrics from saved answers (updates the result files in place).
- `--resume` continues an interrupted run, keeping cases already saved without an error. Without it the output file is overwritten.
- Groq's free tier allows 8,000 tokens per minute, so a run with a Groq judge is slow; the harness waits out rate limits.

Latency is measured with `python -m scripts.measure_latency` (see [`docs/LATENCY-MEASUREMENT-IMPLEMENTATION.md`](docs/LATENCY-MEASUREMENT-IMPLEMENTATION.md)). The latest measurement (14 October) found a P95 of 176.8 s, almost all of it waiting for the LLM's first token on free-tier routing. See `benchmarks/reports/LATENCY_BREAKDOWN_REPORT_2026-10-14.md`.

Metric definitions are in [`docs/EVALUATION.md`](docs/EVALUATION.md). The model comparison (three Groq models, 22 cases) is in `benchmarks/reports/comparison_2026-10-01.md`.

## Troubleshooting

**Uploads stay `pending`.** n8n is not running, the workflow is not active, or the secret does not match. Check `N8N_SHARED_SECRET` in `.env` against the workflow's header, and the n8n execution log. Failed documents can be retried from the Documents page.

**Every retrieval fails with `MissingGreenlet`.** `SUPABASE_DB_URL` is using the asyncpg driver. It must be `postgresql+psycopg2://`.

**Database connection errors.** Check `SUPABASE_DB_URL` against the Supabase dashboard, and that the pgvector extension is enabled ([`docs/DATABASE.md`](docs/DATABASE.md)). Supabase pauses inactive free-tier projects after 7 days: wake it from the dashboard.

**Requests fail or time out.** Free-tier LLM limits and rotating free models are the usual cause. LiteLLM falls back from Gemini to OpenRouter; check `docker compose logs litellm`.

**`/chat` is public.** Chainlit stays unauthenticated if `CHAINLIT_AUTH_SECRET` is not set. Set it in `.env`. In production the app refuses to start without it.

## Contributing

`main` is protected. Branch, PR, squash merge. See [`docs/GIT-WORKFLOW.md`](docs/GIT-WORKFLOW.md) for the enforced branch and commit naming rules.

- **A prompt change is a behaviour change.** Edit [`docs/PROMPTS.md`](docs/PROMPTS.md) and `generator.py` in the same PR, re-run the benchmark, and put the before and after scores in the PR description.
- **A schema change touches two files.** `models.py` and `schema.sql` must stay mirrored.
- **Assistant messages are created with `parent_id=None`** in `app/chainlit/chainlit_app.py`, so they are saved as root messages rather than orphaned child steps.
- **Never commit real credentials.** Add new variables to `.env.example` with empty values.

## Known gaps

- No deployment: there is no hosting, domain or CD. `.github/workflows/deploy.yml` is a commit-message check, not a deploy.
- CI does not run the tests.
- Response time fails the 8 s P95 target (see Running evaluations).
- The reranker, citation chips and grounding gate are in the code but have not been checked with real users. The UAT script was never run.
- Security hardening was descoped: no prompt-injection testing, no automated client-identifier detection, no threat model.
- `mlflow` is not in `requirements.txt`; the harness does not use it, although [`docs/EVALUATION.md`](docs/EVALUATION.md) proposes it.
- The corpus is a set of assumptions: Alfa Focus never confirmed the question set or the document list.

## n8n

n8n runs beside the app in Docker Compose, with workflow and credential data in the named volume `n8n_data` (it survives `docker compose down` and `up`; `down -v` deletes it).

- **`n8n/Document Ingestion.json`** is the workflow the app depends on. A Webhook node (`process-document`) receives the document id from the app, and an HTTP Request node calls `POST http://app:8000/api/n8n/process-document/{id}` with the `X-N8N-Secret` header (from an n8n Header Auth credential). Inside Compose, n8n reaches the app by service name `app`, not `localhost`.
- **`n8n/workflows/fastapi-connectivity-test.json`** is a diagnostic: its webhook `/fastapi-test` calls `http://app:8000/api/n8n-test` and should return `{"status": "ok", "message": "FastAPI successfully reached from n8n"}`.
