from datetime import UTC, datetime

import pytest

from rag_service.models.canonical_document import CanonicalDocument
from rag_service.processing.chunk_metadata import build_document_chunks
from rag_service.processing.chunker import chunk_sections
from rag_service.processing.heading_hierarchy import build_heading_sections
from rag_service.processing.html_parser import parse_html
from rag_service.processing.models import ChunkContent, ContentBlock


def make_document() -> CanonicalDocument:
    return CanonicalDocument(
        document_id="example:article:42",
        source="example",
        source_id="article-42",
        title="Retrieval Guide",
        url="https://docs.example.test/retrieval",
        body="<p>Source body.</p>",
        content_type="article",
        metadata={
            "language": "en-US",
            "topics": ["retrieval"],
        },
        published_at=datetime(2026, 7, 1, tzinfo=UTC),
        modified_at=datetime(2026, 8, 1, tzinfo=UTC),
    )


def make_chunk(text: str, anchor: str | None = None) -> ChunkContent:
    return ChunkContent(
        text=text,
        heading_path=["Guide", "Retrieval"],
        blocks=[
            ContentBlock(block_type="paragraph", text=text),
            ContentBlock(block_type="paragraph", text="Additional context."),
            ContentBlock(block_type="list", text="- First\n- Second"),
        ],
        anchor=anchor,
    )


def test_builds_document_chunks_with_document_and_chunk_metadata() -> None:
    document = make_document()
    chunks = [make_chunk("First.", "retrieval"), make_chunk("Second.")]

    results = build_document_chunks(
        document,
        chunks,
        chunk_id_factory=lambda doc, chunk, sequence: (
            f"{doc.document_id}:temporary:{sequence}"
        ),
    )

    assert [result.sequence for result in results] == [0, 1]
    assert results[0].chunk_id == "example:article:42:temporary:0"
    assert results[0].document_id == document.document_id
    assert results[0].source == document.source
    assert results[0].source_id == document.source_id
    assert results[0].title == document.title
    assert results[0].url == document.url
    assert results[0].content_type == document.content_type
    assert results[0].published_at == document.published_at
    assert results[0].modified_at == document.modified_at
    assert results[0].heading_path == ["Guide", "Retrieval"]
    assert results[0].block_types == ["paragraph", "list"]
    assert results[0].anchor == "retrieval"
    assert results[0].metadata == document.metadata


def test_copies_mutable_metadata_into_each_chunk() -> None:
    document = make_document()

    results = build_document_chunks(
        document,
        [make_chunk("First."), make_chunk("Second.")],
        chunk_id_factory=lambda _document, _chunk, sequence: str(sequence),
    )

    topics = results[0].metadata["topics"]
    assert isinstance(topics, list)
    topics.append("chunking")

    assert results[1].metadata["topics"] == ["retrieval"]
    assert document.metadata["topics"] == ["retrieval"]


def test_builds_metadata_from_the_processing_pipeline() -> None:
    document = make_document()
    document.body = """
        <h2 id="retrieval">Retrieval</h2>
        <p>Retrieve relevant content.</p>
        <ul><li>Embed the query</li><li>Search the index</li></ul>
    """
    chunk_content = chunk_sections(
        build_heading_sections(parse_html(document.body)),
        max_chars=100,
    )

    results = build_document_chunks(
        document,
        chunk_content,
    )

    assert len(results) == 1
    assert results[0].heading_path == ["Retrieval"]
    assert results[0].block_types == ["paragraph", "list"]
    assert results[0].anchor == "retrieval"
    assert results[0].metadata["language"] == "en-US"
    assert results[0].metadata["topics"] == ["retrieval"]
    assert results[0].chunk_id.startswith("example:article:42:chunk:v1:")


def test_preserves_structural_block_metadata_in_document_chunk() -> None:
    document = make_document()
    table_html = "<table><tr><td>Feature</td></tr></table>"
    chunk = ChunkContent(
        text="Feature",
        blocks=[
            ContentBlock(
                block_type="table",
                text="Feature",
                metadata={"html": table_html},
            )
        ],
    )

    result = build_document_chunks(document, [chunk])[0]

    assert result.block_metadata == [
        {
            "block_type": "table",
            "html": table_html,
        }
    ]


def test_default_ids_remain_stable_when_an_earlier_chunk_is_inserted() -> None:
    document = make_document()
    unchanged_chunk = make_chunk("Unchanged content.")

    original = build_document_chunks(document, [unchanged_chunk])
    reindexed = build_document_chunks(
        document,
        [make_chunk("New earlier content."), unchanged_chunk],
    )

    assert original[0].chunk_id == reindexed[1].chunk_id
    assert original[0].sequence == 0
    assert reindexed[1].sequence == 1


def test_rejects_empty_chunk_id() -> None:
    with pytest.raises(ValueError, match="empty chunk ID"):
        build_document_chunks(
            make_document(),
            [make_chunk("Content.")],
            chunk_id_factory=lambda _document, _chunk, _sequence: "",
        )


def test_rejects_duplicate_chunk_ids() -> None:
    with pytest.raises(ValueError, match="duplicate ID"):
        build_document_chunks(
            make_document(),
            [make_chunk("First."), make_chunk("Second.")],
            chunk_id_factory=lambda _document, _chunk, _sequence: "duplicate",
        )
