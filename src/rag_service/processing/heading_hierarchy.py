from rag_service.processing.models import ContentBlock, HeadingSection


def build_heading_sections(blocks: list[ContentBlock]) -> list[HeadingSection]:
    """Group ordered content blocks under their active heading hierarchy.

    Heading levels are interpreted structurally rather than requiring every
    intermediate level to be present. For example, an ``h4`` following an
    ``h2`` becomes a child of that ``h2``. Content before the first heading is
    retained in a section with an empty heading path.
    """

    sections: list[HeadingSection] = []
    heading_stack: list[tuple[int, str]] = []
    current_blocks: list[ContentBlock] = []
    current_path: list[str] = []
    current_anchor: str | None = None

    def flush_section() -> None:
        nonlocal current_blocks
        if current_blocks:
            sections.append(
                HeadingSection(
                    heading_path=current_path,
                    blocks=current_blocks,
                    anchor=current_anchor,
                )
            )
            current_blocks = []

    for block in blocks:
        if block.block_type != "heading":
            current_blocks.append(block)
            continue

        if block.heading_level is None:
            raise ValueError("Heading blocks must include heading_level")

        flush_section()

        while heading_stack and heading_stack[-1][0] >= block.heading_level:
            heading_stack.pop()

        heading_stack.append((block.heading_level, block.text))
        current_path = [heading for _, heading in heading_stack]
        current_anchor = block.anchor

    flush_section()
    return sections
