import pytest

from rag_service.processing.heading_hierarchy import build_heading_sections
from rag_service.processing.html_parser import parse_html
from rag_service.processing.models import ContentBlock


def heading(text: str, level: int, anchor: str | None = None) -> ContentBlock:
    return ContentBlock(
        block_type="heading",
        text=text,
        heading_level=level,
        anchor=anchor,
    )


def paragraph(text: str) -> ContentBlock:
    return ContentBlock(block_type="paragraph", text=text)


def test_builds_nested_heading_paths() -> None:
    sections = build_heading_sections(
        [
            heading("The Living Knowledge System", 1),
            paragraph("Introduction."),
            heading("Knowledge Systems", 2),
            paragraph("System overview."),
            heading("Documentation Infrastructure", 3, "infrastructure"),
            paragraph("Infrastructure details."),
        ]
    )

    assert [section.heading_path for section in sections] == [
        ["The Living Knowledge System"],
        ["The Living Knowledge System", "Knowledge Systems"],
        [
            "The Living Knowledge System",
            "Knowledge Systems",
            "Documentation Infrastructure",
        ],
    ]
    assert sections[-1].anchor == "infrastructure"
    assert sections[-1].blocks == [paragraph("Infrastructure details.")]


def test_replaces_same_level_and_discards_deeper_headings() -> None:
    sections = build_heading_sections(
        [
            heading("Parent", 2),
            heading("First child", 3),
            paragraph("First."),
            heading("Second child", 3),
            paragraph("Second."),
            heading("Next parent", 2),
            paragraph("Next."),
        ]
    )

    assert [section.heading_path for section in sections] == [
        ["Parent", "First child"],
        ["Parent", "Second child"],
        ["Next parent"],
    ]


def test_supports_skipped_heading_levels() -> None:
    sections = build_heading_sections(
        [
            heading("Overview", 2),
            heading("Details", 4),
            paragraph("Content."),
        ]
    )

    assert sections[0].heading_path == ["Overview", "Details"]


def test_retains_content_before_first_heading() -> None:
    sections = build_heading_sections(
        [paragraph("Preamble."), heading("Overview", 2), paragraph("Body.")]
    )

    assert sections[0].heading_path == []
    assert sections[0].blocks == [paragraph("Preamble.")]
    assert sections[1].heading_path == ["Overview"]


def test_keeps_structural_blocks_intact() -> None:
    table = ContentBlock(
        block_type="table",
        text="Feature Description",
        metadata={"html": "<table><tr><td>Feature</td></tr></table>"},
    )
    preserved_component = ContentBlock(
        block_type="html_block",
        text="Interactive component content",
        metadata={"html": '<div class="interactive-component">...</div>'},
    )

    sections = build_heading_sections(
        [heading("Components", 2), table, preserved_component]
    )

    assert sections[0].blocks == [table, preserved_component]


def test_rejects_heading_without_level() -> None:
    malformed_heading = ContentBlock(block_type="heading", text="Overview")

    with pytest.raises(ValueError, match="heading_level"):
        build_heading_sections([malformed_heading])


def test_tracks_hierarchy_from_parsed_html() -> None:
    sections = build_heading_sections(
        parse_html(
            """
            <h1>The Living Knowledge System</h1>
            <h2>Knowledge Systems</h2>
            <h3 id="documentation-infrastructure">
                Documentation Infrastructure
            </h3>
            <p>Infrastructure connects knowledge to its users.</p>
            """
        )
    )

    assert len(sections) == 1
    assert sections[0].heading_path == [
        "The Living Knowledge System",
        "Knowledge Systems",
        "Documentation Infrastructure",
    ]
    assert sections[0].anchor == "documentation-infrastructure"
