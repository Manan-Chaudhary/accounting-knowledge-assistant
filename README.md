# Alfa Focus Knowledge Assistant

An internal, citation-first knowledge assistant for **Alfa Focus**, a specialist SMSF administration practice in South Melbourne. Built as the RMIT COSC2408 Programming Project 1 capstone.

The problem: Australian superannuation rules change constantly - 1 July 2026 alone brought Division 296, payday super, and an indexed transfer balance cap - and firm-specific procedure lives in senior heads rather than in writing. Accountants lose time re-deriving answers, and two staff can give a referring planner two different answers.

The assistant answers two kinds of question and keeps them strictly separate:

- **What does the law require?** Grounded in ATO guidance, rulings, legislation, TPB and APESB, cited to a source you can open.
- **How does Alfa Focus do this?** Grounded in the firm's own procedures, labelled as firm convention rather than law.

Every answer carries resolvable citations and an explicit income year. It assists a registered tax agent; it never signs off.

> **Status: pre-client-meeting.** The client has not been met. Everything in [`docs/CLIENT-BRIEF.md`](docs/CLIENT-BRIEF.md) is open-source research carrying explicit confidence markers. Do not quote a `MEDIUM` or `LOW` fact to the client as settled.

## Documentation

Read in this order. Each is written to be read on its own, but the design decisions only make sense after the domain primer.

| Doc | What it answers |
|---|---|
| [`docs/CLIENT-BRIEF.md`](docs/CLIENT-BRIEF.md) | Who Alfa Focus actually is. **They are an SMSF specialist, not a general tax consultancy** - read this before assuming scope |
| [`docs/DOMAIN-PRIMER.md`](docs/DOMAIN-PRIMER.md) | Australian SMSF practice for a team with no accounting background; what is changing in 2026; the professional-obligation constraints that drive the architecture |
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | Numbered, testable requirements: chatbot behaviour, file upload, data handling, edge cases. What the build is held to |
| [`docs/RAG-DESIGN.md`](docs/RAG-DESIGN.md) | The two-corpus split, the chunk schema, hybrid + temporal retrieval, and **which file in this repo owns each piece** |
| [`docs/PROMPTS.md`](docs/PROMPTS.md) | The system prompt, refusal templates, query-understanding prompt. Source of truth for `app/rag/generator.py` |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Benchmark taxonomy, 28 seed questions, metrics and gates, LLM-judge design, what `/testing` must do |
| [`docs/CLIENT-MEETING-QUESTIONS.md`](docs/CLIENT-MEETING-QUESTIONS.md) | The 14 questions that change the build, ranked |
| [`docs/GIT-WORKFLOW.md`](docs/GIT-WORKFLOW.md) | Branch naming, commit format, PR and CI requirements |
| [`docs/DATABASE.md`](docs/DATABASE.md) | PostgreSQL + pgvector setup, BGE-M3 embeddings, schema reference, connection guide |

## Design principles

These are enforced in code and checked by the evaluation suite, not aspirational:

1. **No citation, no claim.** If retrieval finds nothing, the assistant escalates rather than guesses. A confident unsourced answer is the worst possible output for a regulated client.
2. **Every volatile claim is scoped to an income year.** Undated tax advice is wrong advice.
3. **Law and firm practice are never blended in one sentence.** Separate labelled sections, attributed per claim.
4. **No client identifiers, no member-specific figures.** The assistant answers rules questions. Client data stays out by construction.
5. **Deterministic checks beat judged ones.** Citation resolution is a lookup and an HTTP check, gated at 100% with no exceptions.

## Project structure

```
accounting-knowledge-assistant/
├── app/
│ ├── main.py               # Entry point — registers routes, mounts Chainlit at /chat, then the
│ │                          # built React SPA (frontend/dist) as the catch-all (all mounted LAST)
│ ├── config.py             # Loads all env vars from one place (.env locally, Render env vars in prod)
│ │
│ ├── routes/
│ │ ├── upload.py           # /upload, /documents — document ingest and listing JSON API
│ │ ├── testing.py          # (retired: /testing is now served by the React SPA)
│ │ ├── home.py             # (retired: /home is now served by the React SPA)
│ │ └── auth.py             # /login — prototype login page (real auth flow is a separate task)
│ │
│ ├── chainlit/
│ │ └── chainlit_app.py     # Chat app: on_chat_start, on_message, auth callback
│ │
│ ├── services/
│ │ ├── document_service.py # Document lifecycle, parsing, structure-aware chunking, metadata
│ │ └── storage_service.py  # Supabase Storage: upload/fetch raw files
│ │
│ ├── rag/
│ │ ├── embedder.py         # Text → vector embeddings (BGE-M3 via Hugging Face)
│ │ ├── retriever.py        # Hybrid search: vector
│ │ └── generator.py        # Prompt assembly + LLM call + citation validation
│ │
│ └── db/
│   ├── database.py         # SQLAlchemy session setup and establishes connection
│   ├── models.py           # ORM models: Document, DocumentChunk, AppUser, EvalResult
│   └── schema.sql          # Table definitions — mirrors models.py
│
├── frontend/                # React SPA (Vite + TS) — Home, Documents, Testing, Chat, Login
│ ├── src/
│ │ ├── pages/               # One component per route (ported 1:1 from the old templates/)
│ │ ├── components/          # Shared Sidebar/Layout
│ │ ├── auth/                # AuthProvider/RequireAuth seam for the not-yet-built login flow
│ │ ├── chainlit/             # ChainlitProvider wiring the chat page to /chat via @chainlit/react-client
│ │ └── styles/legacy.css    # Ported verbatim from static/css/style.css, plus a small override block
│ └── dist/                  # `npm run build` output — served by app/main.py in production
│
├── benchmarks/
│   └── questions.jsonl     # Versioned benchmark set — see docs/EVALUATION.md
│
├── tests/                  # Test scripts for database, embeddings, and connections
│
├── templates/              # Jinja2 templates — only login.html remains (real pages are React now)
├── static/                 # Shared CSS (static/css/style.css, still used by templates/login.html)
├── docs/                   # See the documentation table above
│
├── .env.example            # Documents every required env var, no real values
├── Dockerfile
├── requirements.txt        # Pinned dependencies (Chainlit, pgvector, sentence-transformers)
└── README.md
```

### Layer overview

- **`frontend/`** — the React SPA. Owns every page except the prototype login screen; built with `npm run build` and served same-origin by FastAPI (see `app/main.py`'s catch-all route) so the chat session cookie stays same-origin per `docs/LOGIN-PAGE-REQUIREMENTS.md`.
- **`routes/`** — HTTP handlers. `upload.py` and `auth.py` still serve real HTML/JSON; `home.py`/`testing.py` are retired stubs kept only so their routers stay importable. No business logic lives here directly — delegates to `services/`/`rag/`.
- **`chainlit/`** — the chat interface. `on_message` is where a user's question enters the RAG pipeline via `rag/`.
- **`services/`** — logic that isn't HTTP- or chat-specific: document lifecycle and file storage. Keeps `routes/` from growing bloated handlers.
- **`rag/`** — the pipeline itself, split by responsibility (embed → retrieve → generate) so each piece can be tested and swapped independently. `retriever.py` is the highest-value file in the repo: retrieval, not generation, is where RAG systems actually fail.
- **`db/`** — the persistence layer. `models.py` and `schema.sql` mirror each other — update both if the schema changes. The proposed schema is in [`docs/RAG-DESIGN.md`](docs/RAG-DESIGN.md) section 4.

### Database

**Postgres 14+ with pgvector** hosted on **Supabase**. The free tier provides 500MB database storage and 1GB file storage — sufficient for ~1,400 documents with embeddings.

**Why Supabase + pgvector?**
- Single system for metadata filtering, full-text search, and vector similarity
- One SQL query can filter by effective dates, match statutory identifiers, and rank by semantic distance
- No sync lag between separate vector and metadata stores
- Free tier includes automatic backups and point-in-time recovery

- **Dev**: Local development, seeded with test documents (`SUPABASE_DB_URL` in `.env`)

See [`docs/DATABASE.md`](docs/DATABASE.md) for schema details, connection setup, and BGE-M3 embedding integration.

## Local Development Setup

### Prerequisites

- Python 3.13+ (macOS/Linux)
- Active Supabase project with connection string
- Hugging Face account with API token

### Initial Setup

1. **Create virtual environment and install dependencies:**

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment variables:**

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
```bash
# Database
SUPABASE_DB_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

# Embedding model
HF_TOKEN=hf_your_token_here

# LLM providers (choose one or both)
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash

GROQ_API_KEY=your_groq_key
GROQ_MODEL=openai/gpt-oss-120b
```

See [`.env.example`](.env.example) for all variables and [`docs/DATABASE.md`](docs/DATABASE.md) for database setup.

### Running the Application

Chainlit is mounted into FastAPI at `/chat` (see `app/main.py`).

#### Option 1: Running Locally (Uvicorn)

**Development (local access only):**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**LAN access (testing from other devices):**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Running with Docker Compose (Recommended)

Docker Compose automatically loads your `.env` file and mounts your local code into the container for live reloading:

1. **Build and start the application:**
```bash
docker compose up --build

# If you have already built the docker image and simply want to start up the container
docker compose up
```

2. **Run in background (detached mode):**
```bash
docker compose up -d --build
```

3. **Useful Docker Compose commands:**
```bash
# View live container logs
docker compose logs -f

# Stop and remove containers
docker compose down
```

*(Alternatively, you can build and run using raw Docker: `docker build -t alfa-focus-pilot . && docker run -p 8000:8000 --env-file .env alfa-focus-pilot`)*

### Access the Application

| Endpoint | URL | Description |
|---|---|---|
| Web Application (SPA) | `http://localhost:8000/home` | React SPA dashboard (Home) |
| Document Management | `http://localhost:8000/docs` | Document upload and status management (React) |
| Sign In | `http://localhost:8000/login` | Authentication portal |
| Evaluation Suite | `http://localhost:8000/testing` | Benchmark testing runner |
| Chat Interface | `http://localhost:8000/assistant` | Integrated Chainlit chat assistant |
| API Docs | `http://localhost:8000/docs` (API) | FastAPI Swagger UI |
| n8n Workflow Editor | `http://localhost:5678` | n8n automation console |

For LAN access, replace `localhost` with your machine's local IP address.

### Testing

The test suite uses `pytest` and verifies database connections, schema existence, Hugging Face embedding generation, and environment configuration.

Make sure your virtual environment is active and `.env` has valid credentials before running tests:

```bash
source .venv/bin/activate
```

**Run all tests:**
```bash
pytest -v
```

**Run specific test modules:**
```bash
pytest tests/db/{TEST FILE} -v
```

```bash
# Example: running the env loading tests
pytest tests/db/test_env.py -v
```

**Useful pytest flags:**
- `-v`: Verbose output showing each test status
- `-s`: Print stdout messages (useful for viewing embedding dimensions and table lists)
- `-k <pattern>`: Run tests matching a keyword (e.g. `pytest -k "connection"`)

### Troubleshooting

**"Module not found: app"**
- Ensure you're running from the project root, not inside `app/`
- Use `python -m` syntax: `python -m app.main` or specify the full module path: `uvicorn app.main:app`

**"uvicorn: command not found"**
- Activate the virtual environment: `source .venv/bin/activate`
- Or use the direct path: `./.venv/bin/uvicorn app.main:app --reload`

**Database connection errors**
- Verify `SUPABASE_DB_URL` in `.env` matches your Supabase dashboard
- Check that pgvector extension is enabled (see [`docs/DATABASE.md`](docs/DATABASE.md))
- Supabase pauses inactive projects after 7 days — wake it by visiting the dashboard

**Production deployment:**
- Run Uvicorn behind a reverse proxy (nginx)
- Use a process manager (systemd, supervisord)
- Never run as root or bind to privileged ports directly

## Contributing

`main` is protected. Branch, PR, squash merge — see [`docs/GIT-WORKFLOW.md`](docs/GIT-WORKFLOW.md) for the enforced branch and commit naming rules.

Two additional rules for this project:

- **A prompt change is a behaviour change.** Edit [`docs/PROMPTS.md`](docs/PROMPTS.md) and `generator.py` in the same PR, re-run the benchmark, and put the before/after per-class scores in the PR description.
- **A schema change touches two files.** `models.py` and `schema.sql` must stay mirrored.

## Known gaps in the scaffold

Tracked here so nobody assumes they work:

- `.github/workflows/deploy.yml` does not deploy. It contains a commit-message check. Rename it to `commit-message.yml` or make it deploy.
- `app/rag/embedder.py` is empty — BGE-M3 embedding implementation pending (see [`docs/DATABASE.md`](docs/DATABASE.md) for integration guide).
- `app/rag/retriever.py` and `app/rag/generator.py` are incomplete — RAG pipeline scaffolded but not functional.
- `mlflow` is not in `requirements.txt` — the evaluation design in [`docs/EVALUATION.md`](docs/EVALUATION.md) assumes it.
- `ci.yml` has a commented-out `pytest` step — that is where the evaluation gates hook in.

## n8n Workflow Automation

n8n runs as a separate service alongside the FastAPI/Chainlit application using Docker Compose.
### Importing and Running Workflows (Team Reproduction Guide)

To initialise and run the shared workflow in a fresh local environment:

1. **Start the containers**:
   ```bash
   docker compose up --build

### Start the environment

```bash
docker compose up --build
```
Open n8n:
Navigate to http://localhost:5678 in your browser. (Complete the one-time owner setup if prompted).

Import the shared workflow:

In the n8n left navigation bar, go to Workflows.

Click the Add Workflow button (or the three dots menu ... in the top right).

Select Import from File.

Choose the exported file from the repository:

n8n/workflows/fastapi-connectivity-test.json

Execute and Verify:

Click Save and ensure the workflow is active.

Click Test step or trigger the webhook to verify the connection between n8n and FastAPI.

Confirm that the execution log returns the expected JSON response:

{
  "status": "ok",
  "message": "FastAPI successfully reached from n8n"
}

Services:

- FastAPI / Chainlit: `http://localhost:8000`
- n8n editor: `http://localhost:5678`

### FastAPI connectivity test

A test workflow named `FastAPI Connectivity Test` verifies communication between n8n and FastAPI.

The workflow contains:

1. A Webhook trigger at `/fastapi-test`
2. An HTTP Request node that calls `http://app:8000/api/n8n-test`

Docker Compose provides internal DNS, so n8n accesses FastAPI using the service name `app` rather than `localhost`.

Expected response:

```json
{
  "status": "ok",
  "message": "FastAPI successfully reached from n8n"
}
```

The exported workflow is stored at:

`n8n/workflows/fastapi-connectivity-test.json`

### n8n persistence

n8n workflow and credential data is persisted using the named Docker volume:

`n8n_data`

Stopping the services with:

```bash
docker compose down
```

and restarting with:

```bash
docker compose up -d
```

preserves the n8n workflow data.

Do not use `docker compose down -v` unless the n8n volume should intentionally be deleted.
