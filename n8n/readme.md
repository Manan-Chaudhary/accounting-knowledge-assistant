# n8n Document Ingestion Workflow

## Purpose

This workflow receives a document ID after a document is uploaded
to Supabase Storage and triggers the FastAPI document ingestion process.

## Local setup

1. Copy `.env.example` to `.env`.
2. Fill in the required Supabase/database credentials.
3. Start the application and n8n:

```bash
docker compose up -d app n8n