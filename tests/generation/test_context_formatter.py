import json

from rag_service.generation.context_formatter import (
    serialize_context_sources,
    serialize_json,
    serialize_user_message,
    source_record,
)
from rag_service.generation.models import ContextSource
from rag_service.models.chunk import DocumentChunk


def make_source(
    *,
    citation_id: str = "S1",
    title: str = "Understanding RAG",
    text: str = "Retrieval finds relevant content.",
    heading_path: list[str] | None = None,
    score: float = 0.91,
) -> ContextSource:
    """Create a context source for formatter tests."""

    chunk = DocumentChunk(
        chunk_id=f"chunk-{citation_id}",
        document_id=f"document-{citation_id}",
        source="wordpress",
        source_id=citation_id,
        title=title,
        url="https://example.com/understanding-rag",
        content_type="post",
        text=text,
        heading_path=(
            ["Retrieval", "Similarity search"]
            if heading_path is None
            else heading_path
        ),
        sequence=0,
        metadata={},
        published_at=None,
        modified_at=None,
    )

    return ContextSource(
        citation_id=citation_id,
        chunk=chunk,
        score=score,
    )


def test_source_record_includes_only_model_visible_fields() -> None:
    source = make_source()

    record = source_record(source)

    assert record == {
        "citation_id": "S1",
        "title": "Understanding RAG",
        "heading_path": ["Retrieval", "Similarity search"],
        "content": "Retrieval finds relevant content.",
    }
    assert set(record) == {
        "citation_id",
        "title",
        "heading_path",
        "content",
    }


def test_source_record_keeps_an_empty_heading_path() -> None:
    source = make_source(heading_path=[])

    assert source_record(source)["heading_path"] == []


def test_serialize_context_sources_preserves_order_and_text() -> None:
    text = (
        "First paragraph.\n\n"
        "- First item\n"
        "- Second item"
    )
    first_source = make_source(
        citation_id="S1",
        title="First document",
        text=text,
    )
    second_source = make_source(
        citation_id="S2",
        title="Second document",
        text="Second source content.",
    )

    serialized = serialize_context_sources(
        (first_source, second_source)
    )
    decoded = json.loads(serialized)

    assert serialized == serialize_json(
        [
            source_record(first_source),
            source_record(second_source),
        ]
    )
    assert decoded[0]["content"] == text
    assert [item["citation_id"] for item in decoded] == ["S1", "S2"]


def test_serialize_context_sources_returns_an_empty_array() -> None:
    assert serialize_context_sources(()) == "[]"


def test_user_message_embeds_the_counted_source_serialization() -> None:
    source = make_source(text='Line with "quotes" and a \\ slash.')
    sources = (source,)

    user_message = serialize_user_message(
        question="What is retrieval?",
        sources=sources,
    )
    serialized_sources = serialize_context_sources(sources)

    assert serialized_sources in user_message
    assert json.loads(user_message)["sources"] == json.loads(
        serialized_sources
    )
