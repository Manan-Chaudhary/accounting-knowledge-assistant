# Database Architecture: PostgreSQL + pgvector + BGE-M3

> **Status: describes the schema and retrieval as implemented.** `app/db/schema.sql` and `app/db/models.py` are the source of truth. The database is a Supabase project; nothing is deployed beyond local Docker Compose.

This document explains the database architecture, vector embedding strategy, and how PostgreSQL with pgvector powers the RAG retrieval pipeline.

## Overview

The knowledge assistant uses **PostgreSQL with pgvector** hosted on **Supabase** for persistent storage and vector similarity search. Documents are chunked, embedded using **BAAI/bge-m3**, and stored as 1024-dimensional vectors alongside their text content.

### Why PostgreSQL + pgvector?

For Australian SMSF practice, one query must:
- Filter by effective dates (e.g., "rules active in 2025-26 income year")
- Match exact statutory identifiers (e.g., "Div 296", "ITAA 1997 s 292-85")
- Rank by semantic similarity

pgvector allows all three operations in a single SQL query with HNSW or IVFFlat indexing. The alternative — Pinecone or Weaviate for vectors, Postgres for metadata, full-text search in Elasticsearch — means three systems to sync and three round trips per query.

| Environment | Purpose | Connection |
|-------------|---------|------------|
| **Dev** | Local development; the only environment (no production deployment exists) | `SUPABASE_DB_URL` in `.env` |

`SUPABASE_DB_URL` must use the synchronous driver, `postgresql+psycopg2://...`. The asyncpg driver breaks retrieval (`MissingGreenlet`). Chainlit history uses a separate async URL, `CHAINLIT_DATABASE_URL`.

---

## Schema

Defined in two mirrored locations (update both):
- `app/db/schema.sql` — SQL DDL for Supabase SQL editor
- `app/db/models.py` — SQLAlchemy ORM models for Python app

### Core Tables

#### `documents`
Tracks uploaded files and their processing status.

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `filename` | text | Original filename (e.g., `"TR 2024-1.pdf"`) |
| `source_label` | text | Optional label set at upload (nullable; the corpus loader sets it from the manifest). The `"law"` / `"firm"` split is a design intent, not enforced |
| `storage_path` | text | Supabase Storage path to raw file |
| `status` | text | `pending` → `processing` → `ready`, or `failed` |
| `failure_reason` | text | Readable error when `status = 'failed'` |
| `uploaded_by` | text | Email of the signed-in uploader |
| `uploaded_at` | timestamp | Upload timestamp |

#### `document_chunks`
Stores text chunks and their vector embeddings. This is the table queried during retrieval.

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `document_id` | integer | FK → `documents.id` (cascade delete) |
| `chunk_index` | integer | 0-based chunk position in document |
| `section_heading` | text | Nearest heading, kept for citations |
| `content` | text | Chunk text (about 1200 characters with 150 overlap by default; see [`CHUNKING-DESIGN.md`](CHUNKING-DESIGN.md)) |
| `embedding` | vector(1024) | BGE-M3 embedding |

**Constraints:**
- `unique(document_id, chunk_index)` — prevents duplicate chunks on re-ingestion

**Indexes:**
```sql
create index document_chunks_embedding_idx
  on document_chunks using ivfflat (embedding vector_cosine_ops);
```

IVFFlat index accelerates cosine similarity search once the table has substantial data. There is no index on the keyword side: `retrieve_keyword` computes `to_tsvector('english', content)` at query time, which is a sequential scan (fine at this corpus size).

#### `app_users`
Stores users who sign in with email and password. FastAPI owns the session; Chainlit reuses it.

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `email` | text | Unique email |
| `password_hash` | text | bcrypt hash; null means the account cannot sign in |
| `role` | text | `staff`, `admin` or `team` |
| `is_active` | boolean | Inactive users are rejected |
| `created_at` | timestamp | Account creation |

#### `eval_results`
Defined in the schema but **not written by any code**: the evaluation harness and `/testing` page keep results in memory and in JSONL files under `benchmarks/results/`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `question` | text | Benchmark question |
| `expected_answer` | text | Ground truth (if available) |
| `model_name` | text | LLM used (e.g., `"gemini/gemini-3.8-flash"`) |
| `model_answer` | text | Generated answer |
| `accuracy_score` | integer | 0-100 quality score |
| `latency_ms` | integer | Response time |
| `cost_usd` | integer | Inference cost in microdollars |
| `created_at` | timestamp | Evaluation timestamp |

---

## Vector Embeddings with BGE-M3

### Model: BAAI/bge-m3

**BGE-M3** is a multilingual dense retriever from the Beijing Academy of Artificial Intelligence, trained on 700M+ text pairs. It produces 1024-dimensional embeddings optimized for semantic search.

- **Hugging Face**: `BAAI/bge-m3`
- **Output dimension**: 1024
- **Max input tokens**: 8192 (chunks are about 1200 characters, far below that)
- **Normalization**: L2-normalized by default (cosine similarity = dot product)

### Why BGE-M3?

| Criterion | BGE-M3 | Alternatives |
|-----------|--------|--------------|
| **Domain fit** | Trained on academic/technical text, strong on statutory language | OpenAI `text-embedding-3-large` optimized for general web text |
| **Cost** | Hugging Face Inference API (free-tier quota applies) | OpenAI charges $0.13/1M tokens |
| **Latency** | ~200ms per chunk batch (HF serverless) | ~150ms (OpenAI) |
| **Dimensionality** | 1024 (fits IVFFlat index) | 3072 (OpenAI large) — 3× storage |

For a regulated domain with technical jargon (SMSF, SIS Act, CGT), a model trained on formal documents outperforms web-trained embedders.

### Embedding Pipeline

Implemented in `app/rag/embedder.py`: `embed_text()` calls `huggingface_hub.InferenceClient.feature_extraction` with `BAAI/bge-m3` (provider `hf-inference`).

**Flow:**
1. `app/services/document_service.py` `process_document()` downloads the file from Supabase Storage, extracts text and chunks it
2. Each chunk is embedded with one `embed_text()` call (no batching) and checked to be 1024-dimensional
3. Old chunks for the document are deleted first, so reprocessing does not duplicate
4. Chunks are stored in `document_chunks.embedding`, then the document is marked `ready`

**Configuration:**
```python
# app/config.py
HF_TOKEN: str = os.getenv("HF_TOKEN", "")
```

Get your token from https://huggingface.co/settings/tokens and add to `.env`:
```bash
HF_TOKEN=hf_your_token_here
```

### Cosine Similarity Search

pgvector's `vector_cosine_ops` computes cosine similarity between query embedding and stored chunk embeddings:

```sql
SELECT content, 1 - (embedding <=> query_vector) AS similarity
FROM document_chunks
ORDER BY embedding <=> query_vector
LIMIT 10;
```

The `<=>` operator is cosine distance (0 = identical, 2 = opposite). Subtract from 1 to get similarity (1 = identical, -1 = opposite).

---

## Connection Setup

### Local Development

1. **Create Supabase project** at https://supabase.com
2. **Enable pgvector extension** in SQL editor:
   ```sql
   create extension if not exists vector;
   ```
3. **Run schema** from `app/db/schema.sql`
4. **Get connection string** from Project Settings → Database:
   ```
   postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
   ```
5. **Add to `.env`**:
   ```bash
   SUPABASE_DB_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
   ```

### Testing Connection

Run the database test script:

```bash
# From project root
pytest tests/db -v
```

`tests/db/` needs a real `.env` with working Supabase and Hugging Face credentials. `test_check_db.py` runs `SELECT 1`; `test_schema.py` checks the schema.

---

## SQLAlchemy Integration

Located in `app/db/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(settings.SUPABASE_DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**`pool_pre_ping=True`** ensures the connection pool detects stale connections (important for Supabase's serverless architecture).

### ORM Models

Defined in `app/db/models.py` using SQLAlchemy 2.0 syntax:

```python
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

EMBEDDING_DIM = 1024  # BGE-M3 output dimension

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    section_heading = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    
    document = relationship("Document", back_populates="chunks")
```

**Key detail:** `Vector(1024)` is from the `pgvector` Python library. Install via:
```bash
pip install pgvector
```

---

## Retrieval Query Pattern

Implemented in `app/rag/retriever.py` (`retrieve_hybrid`):

1. **Embed query** with BGE-M3
2. **Dense search**: top 20 chunks by cosine distance, joined to `documents` and restricted to `status = 'ready'`
3. **Keyword search**: top 20 chunks by `ts_rank` on `plainto_tsquery('english', ...)`, same `ready` restriction
4. **Reciprocal rank fusion** (`RRF_K = 60`) of the two rankings; the best 20 unique chunks become candidates
5. **Cross-encoder rerank** (`app/rag/reranker.py`, `cross-encoder/ms-marco-MiniLM-L-6-v2` by default, overridable with `RERANKER_MODEL`)
6. **Return top 5** to the generator

There is no recency or income-year ranking and no metadata filter: the temporal retrieval described in [`RAG-DESIGN.md`](RAG-DESIGN.md) is not built.

---

## Storage Costs

Supabase free tier: **500MB database + 1GB file storage**.

**Per-document storage:**
- Raw PDF: ~200KB
- 100 chunks × (512 tokens text + 1024-dim vector): ~150KB
- Total: ~350KB per document

**Capacity:** ~1,400 documents before hitting free tier limit. Upgrade to Pro ($25/mo) for 8GB.

---

## Migration Notes

### If Switching from Pinecone

1. Export vectors from Pinecone
2. Bulk insert into `document_chunks` with `COPY` command (faster than ORM):
   ```bash
   psql $SUPABASE_DB_URL -c "\COPY document_chunks(document_id, chunk_index, content, embedding) FROM 'vectors.csv' CSV"
   ```
3. Build IVFFlat index after bulk load

### If Changing Embedding Model

If switching from BGE-M3 (1024-dim) to another model:

1. Update `EMBEDDING_DIM` in `app/db/models.py`
2. Alter table:
   ```sql
   ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(new_dim);
   ```
3. Drop and recreate index:
   ```sql
   DROP INDEX document_chunks_embedding_idx;
   CREATE INDEX document_chunks_embedding_idx ON document_chunks USING ivfflat (embedding vector_cosine_ops);
   ```
4. Re-embed all documents: call `process_document(document_id)` in `app/services/document_service.py` for each document (it deletes and rebuilds the chunks), or use the retry button / `POST /api/documents/{id}/retry`

---

## Performance Tuning

### Index Choice

| Index Type | Build Time | Query Speed | Memory | When to Use |
|------------|------------|-------------|--------|-------------|
| **IVFFlat** | Fast | Good | Low | <1M vectors, exact recall not critical |
| **HNSW** | Slow | Excellent | High | >1M vectors, low-latency requirements |

For this project, IVFFlat is appropriate. Switch to HNSW if query latency exceeds 200ms with >100k chunks.

### Query Optimization

pgvector scans vectors linearly until index threshold (default: 1000 rows). With <1000 chunks, no index is used — this is expected and fast enough (<50ms).

To force index usage even with small tables:
```sql
SET ivfflat.probes = 10;  -- Higher = more accurate, slower
```

---

## Security

1. **Never commit `SUPABASE_DB_URL`** — it contains the database password. Keep it in `.env` (gitignored).
2. **Rotate Supabase passwords** if leaked. Regenerate from Project Settings → Database.
3. **Enable Row-Level Security (RLS)** on Supabase tables if exposing via PostgREST API (not applicable for this app — direct SQLAlchemy access only).
4. **Restrict IP access** in Supabase dashboard if the app runs from a static IP (not the case for local Docker Compose).

---

## Troubleshooting

### "No module named 'pgvector'"
```bash
pip install pgvector
```

### "Extension 'vector' does not exist"
Run in Supabase SQL editor:
```sql
CREATE EXTENSION vector;
```

### "Connection refused" or timeout
- Check `SUPABASE_DB_URL` in `.env` matches Supabase dashboard
- Verify network connectivity: `psql $SUPABASE_DB_URL -c "SELECT 1;"`
- Supabase pauses inactive projects after 7 days — wake it by visiting the dashboard

### Slow vector search (>500ms)
- Check index exists: `\d document_chunks` in psql
- Rebuild index if stale: `REINDEX INDEX document_chunks_embedding_idx;`
- Profile query: `EXPLAIN ANALYZE SELECT ...`

---

## References

- [pgvector GitHub](https://github.com/pgvector/pgvector) — installation, indexing strategies, performance tuning
- [Supabase pgvector Guide](https://supabase.com/docs/guides/ai/vector-columns) — setup and best practices
- [BGE-M3 Model Card](https://huggingface.co/BAAI/bge-m3) — architecture, training data, benchmarks
- [Hugging Face Inference API](https://huggingface.co/docs/api-inference/index) — serverless embedding endpoint
