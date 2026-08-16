from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rag_service.commands.smoke_answer_generation import (
    SMOKE_QUESTION,
    run,
    write_report,
)
from rag_service.generation.models import (
    ContextSource,
    GeneratedAnswer,
)
from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval.models import RetrievalResult


def make_chunk() -> DocumentChunk:
    """Create one smoke-test document chunk."""

    return DocumentChunk(
        chunk_id="chunk-1",
        document_id="document-1",
        source="wordpress",
        source_id="1",
        title="Heading-aware chunking",
        url="https://example.com/chunking",
        content_type="post",
        text="Heading-aware chunking preserves context.",
        heading_path=["Chunking strategies"],
        sequence=0,
        metadata={},
        published_at=None,
        modified_at=None,
    )


def test_run_generates_answer_from_retrieved_results() -> None:
    chunk = make_chunk()
    retrieval_result = RetrievalResult(
        chunk=chunk,
        score=0.91,
    )
    generated_answer = GeneratedAnswer(
        answer=(
            "Heading-aware chunking preserves context [S1]."
        ),
        sources=(
            ContextSource(
                citation_id="S1",
                chunk=chunk,
                score=0.91,
            ),
        ),
        sufficient_evidence=True,
    )

    retrieval_service = MagicMock()
    retrieval_service.retrieve.return_value = [
        retrieval_result
    ]

    answer_generator = MagicMock()
    answer_generator.generate.return_value = (
        generated_answer
    )

    result = run(
        retrieval_service,
        answer_generator,
    )

    assert result is generated_answer

    request = retrieval_service.retrieve.call_args.args[0]

    assert request.query == SMOKE_QUESTION
    assert request.limit == 5
    assert request.filters == {"source": "wordpress"}

    answer_generator.generate.assert_called_once_with(
        question=SMOKE_QUESTION,
        results=[retrieval_result],
    )


def test_run_rejects_empty_retrieval_results() -> None:
    retrieval_service = MagicMock()
    retrieval_service.retrieve.return_value = []
    answer_generator = MagicMock()

    with pytest.raises(
        RuntimeError,
        match="retrieval returned no qualifying sources",
    ):
        run(
            retrieval_service,
            answer_generator,
        )

    answer_generator.generate.assert_not_called()


def test_run_rejects_insufficient_answer() -> None:
    retrieval_service = MagicMock()
    retrieval_service.retrieve.return_value = [
        RetrievalResult(
            chunk=make_chunk(),
            score=0.91,
        )
    ]

    answer_generator = MagicMock()
    answer_generator.generate.return_value = GeneratedAnswer(
        answer="The available sources are insufficient.",
        sources=(),
        sufficient_evidence=False,
    )

    with pytest.raises(
        RuntimeError,
        match="reported insufficient evidence",
    ):
        run(
            retrieval_service,
            answer_generator,
        )

def test_write_report_includes_answer_and_validated_sources(
    tmp_path: Path,
) -> None:
    chunk = make_chunk()
    answer = GeneratedAnswer(
        answer=(
            "Heading-aware chunking preserves context [S1]."
        ),
        sources=(
            ContextSource(
                citation_id="S1",
                chunk=chunk,
                score=0.91,
            ),
        ),
        sufficient_evidence=True,
    )
    output_path = tmp_path / "answer-report.md"

    result = write_report(
        answer,
        model="gpt-5.6-terra",
        collection="rag_chunks",
        min_score=0.50,
        output_path=output_path,
    )

    assert result == output_path

    report = output_path.read_text(encoding="utf-8")

    assert "# Answer Generation Smoke Test" in report
    assert f"## Question\n\n{SMOKE_QUESTION}" in report
    assert (
        "Heading-aware chunking preserves context [S1]."
        in report
    )
    assert "**Evidence sufficient:** `true`" in report
    assert "### [S1] Heading-aware chunking" in report
    assert "**Retrieval score:** `0.910000`" in report
    assert chunk.text in report