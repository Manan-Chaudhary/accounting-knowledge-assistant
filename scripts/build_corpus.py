"""Download the Corpus A source documents listed in corpus/sources.json.

HTML pages are reduced to their main content and saved as .txt with a
provenance header, because the ingestion pipeline only reads PDF, DOCX and TXT.
PDFs are saved unchanged. Legislation entries resolve the latest compilation
PDF(s) from the Federal Register of Legislation downloads page.

Usage: python scripts/build_corpus.py [--only ID ...]
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "corpus"
SOURCES = CORPUS_DIR / "sources.json"
MANIFEST = CORPUS_DIR / "manifest.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"}
CONTENT_SELECTORS = ["#LawContent", "#lawContents", "article", "#content", "main"]
INLINE_TAGS = ["a", "strong", "em", "b", "i", "span", "abbr", "sup", "sub", "code", "small"]
STRIP_TAGS =["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "button", "svg"]


def html_to_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""

    candidates = [el for sel in CONTENT_SELECTORS if (el := soup.select_one(sel))]
    if not candidates:
        candidates = [soup.body or soup]
    root = max(candidates, key=lambda el: len(el.get_text(" ", strip=True)))

    for tag in root.find_all(STRIP_TAGS):
        tag.decompose()

    for table in root.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if any(cells):
                rows.append(" | ".join(cells))
        table.replace_with(soup.new_string("\n" + "\n".join(rows) + "\n"))

    for level in range(1, 5):
        for h in root.find_all(f"h{level}"):
            h.replace_with(soup.new_string(f"\n\n{'#' * level} {h.get_text(' ', strip=True)}\n"))

    for tag in root.find_all(INLINE_TAGS):
        tag.unwrap()
    for li in root.find_all("li"):
        li.insert(0, soup.new_string("- "))
    root.smooth()

    text = root.get_text("\n")
    text = re.sub(r"^- \n+", "- ", text, flags=re.M)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title, text.strip()


def header_block(src: dict, url: str) -> str:
    lines = [
        f"Title: {src['title']}",
        f"Publisher: {src['publisher']}",
        f"Document type: {src['doc_type']}",
        f"Authority tier: {src['tier']}",
        "Corpus: A (authority)",
        f"Source URL: {src.get('cite_url', url)}",
        f"Retrieved: {date.today().isoformat()}",
        f"Topic: {src['category']}",
    ]
    return "\n".join(lines) + "\n---\n\n"


def legislation_pdfs(client: httpx.Client, title_id: str) -> list[str]:
    page = client.get(f"https://www.legislation.gov.au/{title_id}/latest/downloads")
    page.raise_for_status()
    links = list(dict.fromkeys(re.findall(rf'https://www\.legislation\.gov\.au/{title_id}/[0-9-]+/[0-9-]+/text/[^/"]+/pdf(?:/\d+)?', page.text)))
    original = [u for u in links if "/text/original/" in u]
    return original or links


def fetch(client: httpx.Client, src: dict) -> list[dict]:
    out = []
    if src["kind"] == "legislation":
        urls = legislation_pdfs(client, src["url"])
        if not urls:
            raise ValueError("no compilation PDF found on downloads page")
        for i, url in enumerate(urls, start=1):
            r = client.get(url)
            r.raise_for_status()
            suffix = f"_vol{i}" if len(urls) > 1 else ""
            path = CORPUS_DIR / src["category"] / f"{src['id']}{suffix}.pdf"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(r.content)
            out.append({"file": path, "resolved_url": url})
        return out

    if src.get("sections"):
        parts = []
        for url in [src["url"], *src["sections"]]:
            r = client.get(url)
            r.raise_for_status()
            if str(r.url).rstrip("/") != url.rstrip("/"):
                raise ValueError(f"section {url} redirected to {r.url}")
            page_title, text = html_to_text(r.text)
            parts.append(f"=== Section: {page_title.split(' | ')[0]}\nSource URL: {url}\n\n{text}")
        path = CORPUS_DIR / src["category"] / f"{src['id']}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(header_block(src, src["url"]) + "\n\n".join(parts) + "\n", encoding="utf-8")
        out.append({"file": path, "resolved_url": src["url"], "page_title": src["title"], "opening": f"{len(parts)} sections"})
        return out

    fetch_url = src["url"]
    if src["kind"] == "ruling":
        fetch_url = src["url"].replace("/law/view/document?", "/law/view/print?") + "&PiT=99991231235958"
        src = {**src, "cite_url": src["url"]}
    r = client.get(fetch_url)
    r.raise_for_status()
    if str(r.url).rstrip("/") != fetch_url.rstrip("/") and not src.get("allow_redirect"):
        raise ValueError(f"redirected to {r.url}")

    is_pdf = "pdf" in r.headers.get("content-type", "") or r.content[:4] == b"%PDF"
    path = CORPUS_DIR / src["category"] / f"{src['id']}.{'pdf' if is_pdf else 'txt'}"
    path.parent.mkdir(parents=True, exist_ok=True)

    if is_pdf:
        path.write_bytes(r.content)
    else:
        page_title, text = html_to_text(r.text)
        if len(text) < src.get("min_chars", 800):
            raise ValueError(f"only {len(text)} chars of content extracted")
        path.write_text(header_block(src, str(r.url)) + text + "\n", encoding="utf-8")
        out.append({"file": path, "resolved_url": str(r.url), "page_title": page_title, "opening": text[:160]})
        return out
    out.append({"file": path, "resolved_url": str(r.url)})
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()

    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    failures = []

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=90) as client:
        for src in sources:
            if args.only and src["id"] not in args.only:
                continue
            try:
                results = fetch(client, src)
            except Exception as e:
                failures.append((src["id"], str(e)))
                print(f"FAIL {src['id']}: {e}")
                continue
            files = []
            for res in results:
                rel = res["file"].relative_to(CORPUS_DIR).as_posix()
                files.append({"path": rel, "bytes": res["file"].stat().st_size, "resolved_url": res["resolved_url"],
                              **({"page_title": res["page_title"]} if "page_title" in res else {})})
                if "opening" in res:
                    print(f"     title={res['page_title']!r} | {res['opening'][:110]!r}")
                print(f"ok   {rel} ({res['file'].stat().st_size:,} bytes)")
            manifest[src["id"]] = {**src, "retrieved": date.today().isoformat(), "files": files}

    MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(manifest)} documents in manifest, {len(failures)} failures this run")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
