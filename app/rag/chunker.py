from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingConfig:
    chunk_size: int = 1200
    chunk_overlap: int = 150

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")


@dataclass(frozen=True)
class Chunk:
    document_id: int
    chunk_index: int
    content: str
    section_heading: str | None


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

# Examples:
#   1
#   1.1
#   1.1.1
#   (1)
#   (a)
#   (i)
_CLAUSE_RE = re.compile(
    r"^\s*(?:"
    r"\d+(?:\.\d+)*"
    r"|"
    r"\([a-zA-Z0-9]+\)"
    r"|"
    r"[a-zA-Z]\)"
    r"|"
    r"[ivxlcdm]+\)"
    r")\s+",
    re.IGNORECASE,
)


@dataclass
class _Block:
    content: str
    section_heading: str | None
    kind: str = "text"


def _is_heading(line: str) -> bool:
    return bool(_HEADING_RE.match(line.strip()))


def _heading_text(line: str) -> str:
    match = _HEADING_RE.match(line.strip())
    if not match:
        return line.strip()

    return match.group(2).strip()


def _heading_level(line: str) -> int:
    match = _HEADING_RE.match(line.strip())
    if not match:
        return 0

    return len(match.group(1))


def _is_table_line(line: str) -> bool:
    stripped = line.strip()

    if not stripped:
        return False

    # Supports the pipe-separated tables produced by build_corpus.py.
    return stripped.startswith("|") or "|" in stripped


def _is_clause_start(line: str) -> bool:
    return bool(_CLAUSE_RE.match(line))


def _normalise_lines(text: str) -> list[str]:
    return [
        line.rstrip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]


def _build_blocks(text: str) -> list[_Block]:
    """
    Convert the document into structure-aware blocks.

    Headings update the current section.
    Tables are kept as atomic blocks.
    Numbered clauses are kept together with their continuation lines.
    """
    lines = _normalise_lines(text)

    blocks: list[_Block] = []

    heading_stack: list[tuple[int, str]] = []

    current_lines: list[str] = []
    current_heading: str | None = None
    current_kind = "text"

    def flush() -> None:
        nonlocal current_lines

        content = "\n".join(current_lines).strip()

        if content:
            blocks.append(
                _Block(
                    content=content,
                    section_heading=current_heading,
                    kind=current_kind,
                )
            )

        current_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush()
            continue

        if _is_heading(stripped):
            flush()

            level = _heading_level(stripped)
            heading = _heading_text(stripped)

            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            heading_stack.append((level, heading))

            current_heading = " > ".join(
                item[1] for item in heading_stack
            )
            continue

        # A table starts here. Consecutive pipe-separated lines are kept
        # together as one atomic block.
        if _is_table_line(stripped):
            if current_lines:
                flush()

            table_lines = [stripped]

            # We cannot consume the iterator directly here, so the table
            # continuation handling is performed below by looking at the
            # source lines in a second pass.
            #
            # This block is intentionally handled by _group_table_blocks.
            blocks.append(
                _Block(
                    content=stripped,
                    section_heading=current_heading,
                    kind="table",
                )
            )
            continue

        if current_lines:
            current_lines.append(line)
            continue

        current_lines = [line]
        current_kind = "clause" if _is_clause_start(stripped) else "text"

    flush()

    return _merge_adjacent_table_blocks(blocks)


def _merge_adjacent_table_blocks(blocks: list[_Block]) -> list[_Block]:
    """
    Merge consecutive table blocks so a complete pipe-separated table remains
    one atomic block.
    """
    merged: list[_Block] = []

    for block in blocks:
        if (
            merged
            and block.kind == "table"
            and merged[-1].kind == "table"
            and block.section_heading == merged[-1].section_heading
        ):
            merged[-1].content += "\n" + block.content
        else:
            merged.append(block)

    return merged


def _split_large_text(
    text: str,
    chunk_size: int,
    section_heading: str | None,
) -> list[_Block]:
    """
    Recursively split oversized text using progressively finer separators.
    """
    if len(text) <= chunk_size:
        return [
            _Block(
                content=text.strip(),
                section_heading=section_heading,
            )
        ]

    separators = [
        "\n\n",
        "\n",
        ". ",
        "; ",
        ", ",
        " ",
    ]

    for separator in separators:
        pieces = text.split(separator)

        if len(pieces) <= 1:
            continue

        result: list[_Block] = []
        current = ""

        for piece in pieces:
            candidate = piece if not current else current + separator + piece

            if len(candidate) <= chunk_size:
                current = candidate
                continue

            if current.strip():
                result.extend(
                    _split_large_text(
                        current.strip(),
                        chunk_size,
                        section_heading,
                    )
                )

            current = piece

        if current.strip():
            result.extend(
                _split_large_text(
                    current.strip(),
                    chunk_size,
                    section_heading,
                )
            )

        return result

    # Final fallback for a single extremely long token/line.
    return [
        _Block(
            content=text[start : start + chunk_size].strip(),
            section_heading=section_heading,
        )
        for start in range(0, len(text), chunk_size)
        if text[start : start + chunk_size].strip()
    ]


def _prepare_blocks(
    blocks: list[_Block],
    config: ChunkingConfig,
) -> list[_Block]:
    prepared: list[_Block] = []

    for block in blocks:
        # Tables are intentionally not recursively split. This ensures the
        # table remains complete and self-contained.
        if block.kind == "table":
            prepared.append(block)
            continue

        if len(block.content) <= config.chunk_size:
            prepared.append(block)
            continue

        prepared.extend(
            _split_large_text(
                block.content,
                config.chunk_size,
                block.section_heading,
            )
        )

    return prepared


def _apply_overlap(
    chunks: list[_Block],
    overlap: int,
) -> list[_Block]:
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    result: list[_Block] = []

    for index, chunk in enumerate(chunks):
        if index == 0:
            result.append(chunk)
            continue

        previous = chunks[index - 1]

        # Do not duplicate tables as overlap. The table itself is already
        # preserved as an atomic retrieval unit.
        if previous.kind == "table":
            result.append(chunk)
            continue

        overlap_text = previous.content[-overlap:].strip()

        if not overlap_text:
            result.append(chunk)
            continue

        combined = f"{overlap_text}\n{chunk.content}"

        result.append(
            _Block(
                content=combined,
                section_heading=chunk.section_heading,
                kind=chunk.kind,
            )
        )

    return result


def chunk_document(
    text: str,
    document_id: int,
    config: ChunkingConfig | None = None,
) -> list[Chunk]:
    """
    Structure-aware recursive chunking.

    Preserves:
    - section headings
    - numbered clauses
    - tables
    - document/chunk metadata
    """
    if not text.strip():
        return []

    config = config or ChunkingConfig()

    blocks = _build_blocks(text)
    blocks = _prepare_blocks(blocks, config)

    final_blocks: list[_Block] = []

    current: _Block | None = None

    for block in blocks:
        if current is None:
            current = block
            continue

        # Never combine blocks from different sections.
        if block.section_heading != current.section_heading:
            final_blocks.append(current)
            current = block
            continue

        # Tables remain independent retrieval units.
        if current.kind == "table" or block.kind == "table":
            final_blocks.append(current)
            current = block
            continue

        candidate = f"{current.content}\n\n{block.content}"

        if len(candidate) <= config.chunk_size:
            current = _Block(
                content=candidate,
                section_heading=current.section_heading,
                kind="text",
            )
        else:
            final_blocks.append(current)
            current = block

    if current is not None:
        final_blocks.append(current)

    final_blocks = _apply_overlap(
        final_blocks,
        config.chunk_overlap,
    )

    return [
        Chunk(
            document_id=document_id,
            chunk_index=index,
            content=block.content,
            section_heading=block.section_heading,
        )
        for index, block in enumerate(final_blocks)
        if block.content.strip()
    ]