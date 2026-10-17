from app.rag.chunker import ChunkingConfig, chunk_document


def test_preserves_metadata():
    text = """
# Division 7A

(1) This is the first clause.

(2) This is the second clause.
"""

    chunks = chunk_document(
        text,
        document_id=42,
        config=ChunkingConfig(chunk_size=500, chunk_overlap=50),
    )

    assert chunks

    for index, chunk in enumerate(chunks):
        assert chunk.document_id == 42
        assert chunk.chunk_index == index
        assert chunk.section_heading == "Division 7A"
        assert chunk.content.strip()


def test_preserves_heading():
    text = """
# Division 7A

## Loans

A loan is an arrangement where money is provided to another person.
"""

    chunks = chunk_document(
        text,
        document_id=1,
        config=ChunkingConfig(chunk_size=500, chunk_overlap=50),
    )

    assert len(chunks) == 1
    assert chunks[0].section_heading == "Division 7A > Loans"


def test_keeps_numbered_clause_together():
    text = """
# Application

(1) This section applies to a company.

(2) However, this section does not apply where:
    (a) the company satisfies condition A; and
    (b) the company satisfies condition B.
"""

    chunks = chunk_document(
        text,
        document_id=1,
        config=ChunkingConfig(chunk_size=1000, chunk_overlap=100),
    )

    content = "\n".join(chunk.content for chunk in chunks)

    assert "(2)" in content
    assert "(a)" in content
    assert "(b)" in content


def test_keeps_table_together():
    text = """
# Contribution Caps

The following table shows the contribution caps.

| Year | General cap | Special cap |
| 2024 | $30,000 | $120,000 |
| 2025 | $30,000 | $120,000 |
| 2026 | $30,000 | $120,000 |

These figures are subject to the relevant rules.
"""

    chunks = chunk_document(
        text,
        document_id=1,
        config=ChunkingConfig(chunk_size=100, chunk_overlap=20),
    )

    table_chunks = [
        chunk
        for chunk in chunks
        if "| Year | General cap | Special cap |" in chunk.content
    ]

    assert len(table_chunks) == 1

    table = table_chunks[0].content

    assert "2024" in table
    assert "2025" in table
    assert "2026" in table


def test_chunk_size_is_configurable():
    text = " ".join(["This is some accounting text."] * 200)

    small = chunk_document(
        text,
        document_id=1,
        config=ChunkingConfig(
            chunk_size=200,
            chunk_overlap=20,
        ),
    )

    large = chunk_document(
        text,
        document_id=1,
        config=ChunkingConfig(
            chunk_size=1000,
            chunk_overlap=100,
        ),
    )

    assert len(small) > len(large)


def test_invalid_overlap():
    try:
        ChunkingConfig(
            chunk_size=100,
            chunk_overlap=100,
        )
        assert False
    except ValueError:
        pass