"""Run every corpus file through the ingestion pipeline's own extract and chunk
steps, without Supabase or embeddings, and report per-file chunk counts.

Usage: python scripts/validate_corpus.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# document_service imports the DB engine at module load; a placeholder URL lets it import without connecting.
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://placeholder:placeholder@localhost:5432/placeholder")

from app.services.document_service import chunk_text, extract_text  # noqa: E402

MANIFEST = ROOT / "corpus" / "manifest.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    total_chunks = 0
    failures = 0

    for doc_id, doc in manifest.items():
        for f in doc["files"]:
            path = ROOT / "corpus" / f["path"]
            try:
                text = extract_text(path.read_bytes(), path.name)
                chunks = chunk_text(text)
                if not chunks:
                    raise ValueError("no chunks produced")
            except Exception as e:
                failures += 1
                print(f"FAIL {f['path']}: {e}")
                continue
            f["chars"] = len(text)
            f["chunks"] = len(chunks)
            total_chunks += len(chunks)
            print(f"ok   {f['path']:<75} {len(text):>9,} chars {len(chunks):>5} chunks")

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\n{sum(len(d['files']) for d in manifest.values())} files, {total_chunks:,} chunks, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
