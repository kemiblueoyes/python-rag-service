from rag_service.generation.context_formatter import (
    format_context_source,
    format_context_sources,
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


def test_format_context_source_includes_model_visible_fields() -> None:
    source = make_source()

    formatted = format_context_source(source)

    assert formatted == (
        "[SOURCE S1]\n"
        "Title: Understanding RAG\n"
        "Heading: Retrieval > Similarity search\n"
        "Content:\n"
        "Retrieval finds relevant content.\n"
        "[END SOURCE S1]"
    )


def test_format_context_source_omits_empty_heading_path() -> None:
    source = make_source(
        heading_path=[],
    )

    formatted = format_context_source(source)

    assert formatted == (
        "[SOURCE S1]\n"
        "Title: Understanding RAG\n"
        "Content:\n"
        "Retrieval finds relevant content.\n"
        "[END SOURCE S1]"
    )


def test_format_context_source_preserves_chunk_text() -> None:
    text = (
        "First paragraph.\n\n"
        "- First item\n"
        "- Second item"
    )
    source = make_source(text=text)

    formatted = format_context_source(source)

    assert text in formatted


def test_format_context_sources_preserves_order() -> None:
    first_source = make_source(
        citation_id="S1",
        title="First document",
        text="First source content.",
    )
    second_source = make_source(
        citation_id="S2",
        title="Second document",
        text="Second source content.",
    )

    formatted = format_context_sources(
        (first_source, second_source)
    )

    assert formatted == (
        "[SOURCE S1]\n"
        "Title: First document\n"
        "Heading: Retrieval > Similarity search\n"
        "Content:\n"
        "First source content.\n"
        "[END SOURCE S1]\n\n"
        "[SOURCE S2]\n"
        "Title: Second document\n"
        "Heading: Retrieval > Similarity search\n"
        "Content:\n"
        "Second source content.\n"
        "[END SOURCE S2]"
    )


def test_format_context_sources_returns_empty_string_for_no_sources() -> None:
    assert format_context_sources(()) == ""