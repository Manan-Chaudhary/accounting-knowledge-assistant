import argparse
import csv
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("IngestPipeline")

LOGIN_URL = "http://localhost:8000/api/auth/login"
UPLOAD_URL = "http://localhost:8000/api/upload"
LOG_OUTPUT_PATH = Path("docs/load_log.csv")
BATCH_SIZE = 4
COOLDOWN_SECONDS = 4.0
MAX_RETRIES = 3


def get_prioritized_files(docs_dir: Path) -> List[Path]:
    
    all_files = [f for f in docs_dir.glob("**/*") if f.is_file() and not f.name.startswith(".")]
    smsf_docs, other_docs = [], []
    for f in all_files:
        name_lower = f.name.lower()
        if any(k in name_lower for k in ["smsf", "superannuation", "sis"]):
            smsf_docs.append(f)
        else:
            other_docs.append(f)
    return sorted(smsf_docs) + sorted(other_docs)


def login_session(email: str, password: str) -> requests.Session:
    
    session = requests.Session()
    logger.info("Authenticating with %s ...", email)
    resp = session.post(
        LOGIN_URL,
        json={"email": email, "password": password},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed [{resp.status_code}]: {resp.text}")
    logger.info("Login successful. Session established.")
    return session


def upload_document(session: requests.Session, file_path: Path) -> Dict[str, Any]:
    retries = 0
    start_time = time.time()

    while retries < MAX_RETRIES:
        try:
            with open(file_path, "rb") as f:
                response = session.post(
                    UPLOAD_URL,
                    files={"file": (file_path.name, f, "application/octet-stream")},
                    timeout=120,
                    allow_redirects=False,
                )

            
            if response.status_code == 307:
                raise RuntimeError("Session expired or redirected to /login.")

            if response.status_code in (429, 502, 503, 504):
                retries += 1
                wait_sec = (2 ** retries) + 1
                logger.warning("Quota or busy (%s) on %s. Backoff %ss...", response.status_code, file_path.name, wait_sec)
                time.sleep(wait_sec)
                continue

            response.raise_for_status()
            duration = round(time.time() - start_time, 2)
            
            resp_data = {}
            try:
                resp_data = response.json()
            except Exception:
                pass

            doc_id = resp_data.get("id") or resp_data.get("document_id") or "created"

            return {
                "file_name": file_path.name,
                "document_id": doc_id,
                "status": "PROCESSED",
                "duration_seconds": duration,
                "error": "",
            }

        except Exception as e:
            retries += 1
            if retries >= MAX_RETRIES:
                return {
                    "file_name": file_path.name,
                    "document_id": "N/A",
                    "status": "FAILED",
                    "duration_seconds": round(time.time() - start_time, 2),
                    "error": str(e),
                }
            time.sleep(2 ** retries)

    return {"file_name": file_path.name, "document_id": "N/A", "status": "FAILED", "duration_seconds": 0, "error": "Unknown"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", type=str, required=True, help="User email for login")
    parser.add_argument("--password", type=str, required=True, help="User password for login")
    parser.add_argument("--docs-dir", type=str, default="corpus", help="Corpus directory path")
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    if not docs_dir.exists():
        logger.error("Directory '%s' does not exist.", docs_dir)
        return

    session = login_session(args.email, args.password)
    files = get_prioritized_files(docs_dir)
    total = len(files)
    logger.info("Found %s files. Starting prioritized batch ingestion...", total)

    LOG_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file_name", "document_id", "status", "duration_seconds", "error"])
        writer.writeheader()

    for idx in range(0, total, BATCH_SIZE):
        batch = files[idx: idx + BATCH_SIZE]
        batch_no = (idx // BATCH_SIZE) + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info("Processing Batch %s/%s (%s files)...", batch_no, total_batches, len(batch))

        for file_path in batch:
            record = upload_document(session, file_path)
            logger.info("File: %s -> %s", file_path.name, record["status"])

            with open(LOG_OUTPUT_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["file_name", "document_id", "status", "duration_seconds", "error"])
                writer.writerow(record)

        if idx + BATCH_SIZE < total:
            time.sleep(COOLDOWN_SECONDS)

    logger.info("All documents completed. Results written to %s", LOG_OUTPUT_PATH)


if __name__ == "__main__":
    main()