from pathlib import Path

from app.rag.chunker import ChunkingConfig, chunk_document


SAMPLES = [
    (
        1,
        Path("corpus/general-tax/division-7a/ato-division-7a.txt"),
    ),
    (
        2,
        Path("corpus/smsf-contributions/ato-contributions-caps-table.txt"),
    ),
    (
        3,
        Path("corpus/legislation/leg-tax-agent-services-act-2009.pdf"),
    ),
]


def main():
    config = ChunkingConfig(
        chunk_size=1200,
        chunk_overlap=150,
    )

    for document_id, path in SAMPLES:
        print("=" * 80)
        print(f"DOCUMENT {document_id}: {path}")
        print("=" * 80)

        if path.suffix.lower() == ".pdf":
            import pymupdf

            with pymupdf.open(path) as pdf:
                text = "\n".join(page.get_text() for page in pdf)
        else:
            text = path.read_text(encoding="utf-8")

        chunks = chunk_document(
            text=text,
            document_id=document_id,
            config=config,
        )

        print(f"Chunks: {len(chunks)}")

        for chunk in chunks[:3]:
            print("\n---")
            print(f"document_id: {chunk.document_id}")
            print(f"chunk_index: {chunk.chunk_index}")
            print(f"section_heading: {chunk.section_heading}")
            print(f"content:\n{chunk.content[:500]}")


if __name__ == "__main__":
    main()