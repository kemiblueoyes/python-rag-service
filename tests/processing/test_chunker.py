import pytest

from rag_service.processing.chunker import chunk_sections
from rag_service.processing.heading_hierarchy import build_heading_sections
from rag_service.processing.html_parser import parse_html
from rag_service.processing.models import ContentBlock, HeadingSection


def paragraph(text: str) -> ContentBlock:
    return ContentBlock(block_type="paragraph", text=text)


def test_preserves_heading_paths_anchors_and_section_boundaries() -> None:
    sections = [
        HeadingSection(
            heading_path=["Guide", "First"],
            blocks=[paragraph("First section.")],
            anchor="first",
        ),
        HeadingSection(
            heading_path=["Guide", "Second"],
            blocks=[paragraph("Second section.")],
            anchor="second",
        ),
    ]

    chunks = chunk_sections(sections, max_chars=100)

    assert [chunk.heading_path for chunk in chunks] == [
        ["Guide", "First"],
        ["Guide", "Second"],
    ]
    assert [chunk.anchor for chunk in chunks] == ["first", "second"]


def test_groups_blocks_until_size_limit() -> None:
    section = HeadingSection(
        heading_path=["Overview"],
        blocks=[paragraph("12345"), paragraph("67890"), paragraph("abc")],
    )

    chunks = chunk_sections([section], max_chars=12)

    assert [chunk.text for chunk in chunks] == ["12345\n\n67890", "abc"]


@pytest.mark.parametrize(
    "block_type",
    ["list", "code", "quote", "table", "html_block"],
)
def test_keeps_structural_blocks_intact_when_oversized(block_type: str) -> None:
    rich_block = ContentBlock(block_type=block_type, text="x" * 25)  # type: ignore[arg-type]
    section = HeadingSection(
        heading_path=["Components"],
        blocks=[paragraph("Before."), rich_block, paragraph("After.")],
    )

    chunks = chunk_sections([section], max_chars=10)

    assert [chunk.text for chunk in chunks] == ["Before.", "x" * 25, "After."]
    assert chunks[1].blocks == [rich_block]


def test_splits_oversized_paragraph_at_word_boundaries() -> None:
    section = HeadingSection(
        heading_path=["Details"],
        blocks=[paragraph("alpha beta gamma delta")],
        anchor="details",
    )

    chunks = chunk_sections([section], max_chars=10)

    assert [chunk.text for chunk in chunks] == ["alpha beta", "gamma", "delta"]
    assert all(len(chunk.text) <= 10 for chunk in chunks)
    assert all(chunk.anchor == "details" for chunk in chunks)


def test_slices_a_word_that_exceeds_the_limit() -> None:
    section = HeadingSection(blocks=[paragraph("abcdefghijkl")])

    chunks = chunk_sections([section], max_chars=5)

    assert [chunk.text for chunk in chunks] == ["abcde", "fghij", "kl"]


def test_chunks_parsed_html_under_the_correct_heading() -> None:
    sections = build_heading_sections(
        parse_html(
            """
            <h2 id="retrieval">Retrieval</h2>
            <p>Retrieve relevant content.</p>
            <ul><li>Embed the query</li><li>Search the index</li></ul>
            """
        )
    )

    chunks = chunk_sections(sections, max_chars=100)

    assert len(chunks) == 1
    assert chunks[0].heading_path == ["Retrieval"]
    assert chunks[0].anchor == "retrieval"
    assert [block.block_type for block in chunks[0].blocks] == [
        "paragraph",
        "list",
    ]


def test_rejects_non_positive_size_limit() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        chunk_sections([], max_chars=0)
