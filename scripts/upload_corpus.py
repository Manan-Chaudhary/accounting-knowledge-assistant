"""Upload every corpus file through the app's POST /upload endpoint, which stores
the file in Supabase Storage, inserts the documents row, and fires the n8n
process-document webhook. Then poll each document until it is ready or failed.

Requires the app and n8n running (docker compose up -d app n8n) with real
Supabase and HF credentials in .env. On builds with session auth, also set
CORPUS_UPLOAD_EMAIL / CORPUS_UPLOAD_PASSWORD for an app_users login.

Usage:
  python scripts/upload_corpus.py [--base-url http://localhost:8000] [--only ID ...] [--dry-run]
"""
import argparse
import json
import mimetypes
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "corpus" / "manifest.json"
LOG = ROOT / "corpus" / "upload_log.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=900)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = [
        (doc_id, ROOT / "corpus" / f["path"])
        for doc_id, doc in manifest.items()
        if not args.only or doc_id in args.only
        for f in doc["files"]
    ]
    if args.dry_run:
        for doc_id, path in files:
            print(f"would upload {doc_id}: {path.relative_to(ROOT)}")
        return 0

    email = os.environ.get("CORPUS_UPLOAD_EMAIL")
    password = os.environ.get("CORPUS_UPLOAD_PASSWORD")
    log = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}

    with httpx.Client(base_url=args.base_url, timeout=120) as client:
        # Builds without the session-auth middleware have no /api/auth/login, so only log in when credentials are given.
        if email and password:
            client.post("/api/auth/login", json={"email": email, "password": password}).raise_for_status()

        for doc_id, path in files:
            key = path.relative_to(ROOT / "corpus").as_posix()
            if log.get(key, {}).get("status") == "ready":
                print(f"skip {key} (already ready as document {log[key]['document_id']})")
                continue
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            with path.open("rb") as fh:
                r = client.post("/upload", files={"file": (path.name, fh, content_type)})
            if r.status_code >= 400:
                log[key] = {"status": "upload_failed", "detail": r.text[:500]}
                print(f"FAIL upload {key}: {r.status_code} {r.text[:200]}")
                continue
            document_id = r.json()["document"]["id"]
            log[key] = {"document_id": document_id, "status": "pending"}
            print(f"sent {key} -> document {document_id}")

        deadline = time.time() + args.poll_seconds
        pending = [k for k, v in log.items() if v.get("status") in ("pending", "processing")]
        while pending and time.time() < deadline:
            time.sleep(10)
            for key in list(pending):
                r = client.get(f"/documents/{log[key]['document_id']}/status")
                if r.status_code == 200:
                    log[key]["status"] = r.json()["status"]
                if log[key]["status"] in ("ready", "failed"):
                    pending.remove(key)
                    print(f"{log[key]['status']:<8} {key}")

    LOG.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    counts = {}
    for v in log.values():
        counts[v["status"]] = counts.get(v["status"], 0) + 1
    print(f"\nstatus counts: {counts}")
    return 0 if set(counts) <= {"ready"} else 1


if __name__ == "__main__":
    sys.exit(main())
