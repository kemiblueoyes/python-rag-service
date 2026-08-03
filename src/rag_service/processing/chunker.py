from rag_service.processing.models import ChunkContent, ContentBlock, HeadingSection

DEFAULT_MAX_CHARS = 2_000
_SEPARATOR = "\n\n"
_ATOMIC_BLOCK_TYPES = {"list", "code", "quote", "table", "html_block"}


def chunk_sections(
    sections: list[HeadingSection],
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[ChunkContent]:
    """Split heading sections into bounded chunks without breaking rich blocks.

    Section boundaries are always preserved. Lists, code, quotes, tables, and
    preserved HTML components are atomic (kept together as one complete piece);
    when one is larger than max_chars, it is emitted intact as an oversized chunk.
    Oversized paragraphs use a deterministic whitespace-aware fallback.
    """

    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")

    chunks: list[ChunkContent] = []

    for section in sections:
        current_blocks: list[ContentBlock] = []

        for block in section.blocks:
            if block.block_type in _ATOMIC_BLOCK_TYPES:
                if _combined_length(current_blocks, block.text) > max_chars:
                    current_blocks = _flush_chunk(chunks, current_blocks, section)

                current_blocks.append(block)

                if len(block.text) > max_chars:
                    current_blocks = _flush_chunk(chunks, current_blocks, section)
                continue

            for block_part in _split_block(block, max_chars):
                if _combined_length(current_blocks, block_part.text) > max_chars:
                    current_blocks = _flush_chunk(chunks, current_blocks, section)
                current_blocks.append(block_part)

        _flush_chunk(chunks, current_blocks, section)

    return chunks


def _flush_chunk(
    chunks: list[ChunkContent],
    blocks: list[ContentBlock],
    section: HeadingSection,
) -> list[ContentBlock]:
    if blocks:
        chunks.append(
            ChunkContent(
                text=_render_blocks(blocks),
                heading_path=section.heading_path,
                blocks=blocks,
                anchor=section.anchor,
            )
        )
    return []


def _render_blocks(blocks: list[ContentBlock]) -> str:
    return _SEPARATOR.join(block.text for block in blocks)


def _combined_length(blocks: list[ContentBlock], next_text: str) -> int:
    if not blocks:
        return len(next_text)
    return len(_render_blocks(blocks)) + len(_SEPARATOR) + len(next_text)


def _split_block(block: ContentBlock, max_chars: int) -> list[ContentBlock]:
    if len(block.text) <= max_chars:
        return [block]

    return [
        block.model_copy(update={"text": text_part})
        for text_part in _split_text(block.text, max_chars)
    ]


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split text at whitespace where possible, slicing overlong words."""

    parts: list[str] = []
    remaining = text

    while len(remaining) > max_chars:
        split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at <= 0:
            split_at = max_chars

        parts.append(remaining[:split_at])
        remaining = remaining[split_at:]
        if remaining.startswith(" "):
            remaining = remaining[1:]

    if remaining:
        parts.append(remaining)

    return parts
