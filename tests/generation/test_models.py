import pytest
from pydantic import ValidationError

from rag_service.generation.models import (
    AssembledContext,
    ContextSource,
    ProposedAnswer,
)
from rag_service.models.chunk import DocumentChunk


def make_chunk(
    *,
    chunk_id: str = "chunk-1",
    document_id: str = "document-1",
    title: str = "Understanding RAG",
    text: str = "Retrieval finds relevant content.",
    heading_path: list[str] | None = None,
    sequence: int = 0,
) -> DocumentChunk:
    """Create a document chunk for generation model tests."""

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source="wordpress",
        source_id="42",
        title=title,
        url="https://example.com/understanding-rag",
        content_type="post",
        text=text,
        heading_path=heading_path or ["Retrieval"],
        sequence=sequence,
        metadata={"target_audience": ["Technical Writer"]},
        published_at=None,
        modified_at=None,
    )


def test_context_source_retains_chunk_and_retrieval_score() -> None:
    chunk = make_chunk()

    source = ContextSource(
        citation_id="S1",
        chunk=chunk,
        score=0.91,
    )

    assert source.citation_id == "S1"
    assert source.chunk is chunk
    assert source.chunk.chunk_id == "chunk-1"
    assert source.chunk.source_id == "42"
    assert source.chunk.heading_path == ["Retrieval"]
    assert source.score == 0.91


def test_assembled_context_preserves_source_order() -> None:
    first_source = ContextSource(
        citation_id="S1",
        chunk=make_chunk(
            chunk_id="chunk-1",
            sequence=0,
        ),
        score=0.93,
    )
    second_source = ContextSource(
        citation_id="S2",
        chunk=make_chunk(
            chunk_id="chunk-2",
            document_id="document-2",
            sequence=1,
        ),
        score=0.87,
    )

    context = AssembledContext(
        sources=(first_source, second_source),
        token_count=125,
    )

    assert context.sources == (first_source, second_source)
    assert context.sources[0].citation_id == "S1"
    assert context.sources[1].citation_id == "S2"
    assert context.token_count == 125


def test_assembled_context_can_be_empty() -> None:
    context = AssembledContext(
        sources=(),
        token_count=0,
    )

    assert context.sources == ()
    assert context.token_count == 0


def test_assembled_context_rejects_negative_token_count() -> None:
    with pytest.raises(
        ValueError,
        match="token_count must be zero or greater",
    ):
        AssembledContext(
            sources=(),
            token_count=-1,
        )

def test_proposed_answer_accepts_sufficient_evidence() -> None:
    answer = ProposedAnswer(
        answer="RAG uses retrieved evidence [S1].",
        citation_ids=["S1"],
        sufficient_evidence=True,
    )

    assert answer.sufficient_evidence is True
    assert answer.citation_ids == ["S1"]


def test_proposed_answer_accepts_insufficient_evidence() -> None:
    answer = ProposedAnswer(
        answer="The available sources are insufficient.",
        citation_ids=[],
        sufficient_evidence=False,
    )

    assert answer.sufficient_evidence is False
    assert answer.citation_ids == []


def test_proposed_answer_rejects_sufficient_answer_without_citations() -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "sufficient answers must contain at least one citation ID"
        ),
    ):
        ProposedAnswer(
            answer="RAG uses retrieved evidence.",
            citation_ids=[],
            sufficient_evidence=True,
        )


def test_proposed_answer_rejects_insufficient_answer_with_citations() -> None:
    with pytest.raises(
        ValidationError,
        match="insufficient answers must not contain citation IDs",
    ):
        ProposedAnswer(
            answer="The available sources are insufficient [S1].",
            citation_ids=["S1"],
            sufficient_evidence=False,
        )