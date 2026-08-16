import pytest

from rag_service.generation.citation_validator import (
    CitationValidator,
)
from rag_service.generation.errors import CitationValidationError
from rag_service.generation.models import (
    AssembledContext,
    ContextSource,
    ProposedAnswer,
)
from rag_service.models.chunk import DocumentChunk


def make_source(citation_id: str) -> ContextSource:
    """Create one context source for citation tests."""

    chunk = DocumentChunk(
        chunk_id=f"chunk-{citation_id}",
        document_id=f"document-{citation_id}",
        source="wordpress",
        source_id=citation_id,
        title="Understanding RAG",
        url="https://example.com/rag",
        content_type="post",
        text="Retrieval finds relevant content.",
        heading_path=["Retrieval"],
        sequence=0,
        metadata={},
        published_at=None,
        modified_at=None,
    )

    return ContextSource(
        citation_id=citation_id,
        chunk=chunk,
        score=0.90,
    )


def make_context() -> AssembledContext:
    """Create context containing two available sources."""

    return AssembledContext(
        sources=(
            make_source("S1"),
            make_source("S2"),
        ),
        token_count=100,
    )


def test_citation_validator_accepts_valid_citations() -> None:
    answer = ProposedAnswer(
        answer=(
            "RAG uses retrieval [S1]. "
            "Retrieved content supports generation [S2]."
        ),
        citation_ids=["S1", "S2"],
        sufficient_evidence=True,
    )

    result = CitationValidator().validate(
        answer=answer,
        context=make_context(),
    )

    assert result is answer


def test_citation_validator_allows_repeated_inline_citation() -> None:
    answer = ProposedAnswer(
        answer="Retrieval finds content [S1]. It supports answers [S1].",
        citation_ids=["S1"],
        sufficient_evidence=True,
    )

    result = CitationValidator().validate(
        answer=answer,
        context=make_context(),
    )

    assert result is answer


def test_citation_validator_accepts_insufficient_answer() -> None:
    answer = ProposedAnswer(
        answer="The available sources are insufficient.",
        citation_ids=[],
        sufficient_evidence=False,
    )

    result = CitationValidator().validate(
        answer=answer,
        context=AssembledContext(
            sources=(),
            token_count=0,
        ),
    )

    assert result is answer


def test_citation_validator_rejects_unknown_source() -> None:
    answer = ProposedAnswer(
        answer="RAG uses retrieval [S3].",
        citation_ids=["S3"],
        sufficient_evidence=True,
    )

    with pytest.raises(
        CitationValidationError,
        match="sources that were not supplied",
    ):
        CitationValidator().validate(
            answer=answer,
            context=make_context(),
        )


def test_citation_validator_rejects_missing_inline_citation() -> None:
    answer = ProposedAnswer(
        answer="RAG uses retrieval [S1].",
        citation_ids=["S1", "S2"],
        sufficient_evidence=True,
    )

    with pytest.raises(
        CitationValidationError,
        match="inline citations do not match",
    ):
        CitationValidator().validate(
            answer=answer,
            context=make_context(),
        )


def test_citation_validator_rejects_undeclared_inline_citation() -> None:
    answer = ProposedAnswer(
        answer="RAG uses retrieval [S1] and generation [S2].",
        citation_ids=["S1"],
        sufficient_evidence=True,
    )

    with pytest.raises(
        CitationValidationError,
        match="inline citations do not match",
    ):
        CitationValidator().validate(
            answer=answer,
            context=make_context(),
        )


def test_citation_validator_rejects_malformed_inline_citation() -> None:
    answer = ProposedAnswer(
        answer="RAG uses retrieval [S01].",
        citation_ids=["S1"],
        sufficient_evidence=True,
    )

    with pytest.raises(
        CitationValidationError,
        match="malformed inline citations",
    ):
        CitationValidator().validate(
            answer=answer,
            context=make_context(),
        )