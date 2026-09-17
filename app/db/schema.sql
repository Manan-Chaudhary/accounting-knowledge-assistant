-- Run this in each Supabase project's SQL editor
-- Mirrors app/db/models.py.

create extension if not exists vector;

create table if not exists documents (
    id serial primary key,
    filename text not null,
    source_label text,
    storage_path text,
    status text not null default 'pending', -- 'pending' | 'ready' | 'failed'
    failure_reason text,
    uploaded_by text,
    uploaded_at timestamp default now()
);

create table if not exists document_chunks (
    id serial primary key,
    document_id integer references documents(id) on delete cascade,
    chunk_index integer not null,
    content text not null,
    embedding vector(1024) not null,  -- BGE-M3 output dimension
    unique(document_id, chunk_index)  -- idempotent re-ingestion, no duplicate chunks
);

-- index for fast similarity search once there's real data
create index if not exists document_chunks_embedding_idx
    on document_chunks using ivfflat (embedding vector_cosine_ops);

create table if not exists app_users (
    id serial primary key,
    email text unique not null,
    role text not null default 'staff',  -- 'staff' | 'admin'
    created_at timestamp default now()
);

create table if not exists eval_results (
    id serial primary key,
    question text not null,
    expected_answer text,
    model_name text not null,
    model_answer text,
    accuracy_score integer,
    latency_ms integer,
    cost_usd integer,
    created_at timestamp default now()
);