import pytest

from rag_service.evaluation.answers import evaluate_answer_case
from rag_service.evaluation.models import (
    AnswerExpectation,
    EvaluationCase,
    GoldSource,
    RetrievalExpectation,
)
from rag_service.generation.models import (
    ContextSource,
    GeneratedAnswer,
)
from rag_service.models.chunk import DocumentChunk


def _chunk(chunk_id: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="wordpress:page:1",
        source="wordpress",
        source_id="1",
        title="Test document",
        url="https://example.com/test",
        content_type="page",
        text="Supporting content.",
        heading_path=["Test section"],
        sequence=0,
    )


def _answerable_case() -> EvaluationCase:
    return EvaluationCase(
        id="answerable-001",
        category="exact_answer",
        query="What does the documentation say?",
        retrieval=RetrievalExpectation(
            relevant_sources=[
                GoldSource(
                    document_id="wordpress:page:1",
                    title="Test document",
                    heading_path=["Test section"],
                    chunk_id="chunk-1",
                )
            ],
        ),
        answer=AnswerExpectation(
            expected_sufficient_evidence=True,
            required_points=["Explain the documented behavior."],
        ),
    )


def _unanswerable_case() -> EvaluationCase:
    return EvaluationCase(
        id="unanswerable-001",
        category="unanswerable",
        query="What is not covered?",
        retrieval=RetrievalExpectation(
            expect_empty=True,
        ),
        answer=AnswerExpectation(
            expected_sufficient_evidence=False,
        ),
    )


def test_answerable_case_passes_with_acceptable_citation() -> None:
    case = _answerable_case()

    answer = GeneratedAnswer(
        answer="The documentation explains the behavior. [S1]",
        sources=(
            ContextSource(
                citation_id="S1",
                chunk=_chunk("chunk-1"),
                score=0.9,
            ),
        ),
        sufficient_evidence=True,
    )

    result = evaluate_answer_case(case, answer)

    assert result.sufficiency_correct is True
    assert result.citation_behavior_correct is True
    assert result.unacceptable_citation_chunk_ids == ()
    assert result.passed is True


def test_answerable_case_fails_without_citations() -> None:
    case = _answerable_case()

    answer = GeneratedAnswer(
        answer="The documentation explains the behavior.",
        sources=(),
        sufficient_evidence=True,
    )

    result = evaluate_answer_case(case, answer)

    assert result.citation_behavior_correct is False
    assert result.passed is False


def test_unanswerable_case_fails_when_answer_includes_citation() -> None:
    case = _unanswerable_case()

    answer = GeneratedAnswer(
        answer="The documentation explains the behavior. [S1]",
        sources=(
            ContextSource(
                citation_id="S1",
                chunk=_chunk("chunk-1"),
                score=0.9,
            ),
        ),
        sufficient_evidence=False,
    )

    result = evaluate_answer_case(case, answer)

    assert result.citation_behavior_correct is False
    assert result.passed is False


def test_answerable_case_fails_with_unacceptable_citation() -> None:
    case = _answerable_case()

    answer = GeneratedAnswer(
        answer="The documentation explains the behavior. [S1]",
        sources=(
            ContextSource(
                citation_id="S1",
                chunk=_chunk("chunk-2"),
                score=0.9,
            ),
        ),
        sufficient_evidence=True,
    )

    result = evaluate_answer_case(case, answer)

    assert result.sufficiency_correct is True
    assert result.citation_behavior_correct is False
    assert result.unacceptable_citation_chunk_ids == ("chunk-2",)
    assert result.passed is False


def test_unanswerable_case_passes_when_answer_is_declined() -> None:
    case = _unanswerable_case()

    answer = GeneratedAnswer(
        answer="The available sources do not contain enough information.",
        sources=(),
        sufficient_evidence=False,
    )

    result = evaluate_answer_case(case, answer)

    assert result.sufficiency_correct is True
    assert result.citation_behavior_correct is True
    assert result.passed is True


def test_answerable_case_fails_when_evidence_marked_insufficient() -> None:
    case = _answerable_case()

    answer = GeneratedAnswer(
        answer="The available sources do not contain enough information.",
        sources=(),
        sufficient_evidence=False,
    )

    result = evaluate_answer_case(case, answer)

    assert result.sufficiency_correct is False
    assert result.citation_behavior_correct is False
    assert result.passed is False


def test_case_without_answer_expectation_cannot_be_evaluated() -> None:
    case = _answerable_case().model_copy(
        update={"answer": None}
    )

    answer = GeneratedAnswer(
        answer="An answer.",
        sources=(),
        sufficient_evidence=False,
    )

    with pytest.raises(
        ValueError,
        match="has no answer expectation",
    ):
        evaluate_answer_case(case, answer)

def test_answerable_case_fails_with_only_supporting_citation() -> None:
    case = EvaluationCase(
        id="answerable-001",
        category="exact_answer",
        query="What does the documentation say?",
        retrieval=RetrievalExpectation(
            relevant_sources=[
                GoldSource(
                    document_id="wordpress:page:1",
                    title="Test document",
                    heading_path=["Primary section"],
                    chunk_id="chunk-primary",
                ),
                GoldSource(
                    document_id="wordpress:page:1",
                    title="Test document",
                    heading_path=["Supporting section"],
                    chunk_id="chunk-supporting",
                    role="supporting",
                ),
            ],
        ),
        answer=AnswerExpectation(
            expected_sufficient_evidence=True
        ),
    )

    answer = GeneratedAnswer(
        answer="The documentation explains the behavior. [S1]",
        sources=(
            ContextSource(
                citation_id="S1",
                chunk=_chunk("chunk-supporting"),
                score=0.9,
            ),
        ),
        sufficient_evidence=True,
    )

    result = evaluate_answer_case(case, answer)

    assert result.primary_citation_present is False
    assert result.citation_behavior_correct is False
    assert result.passed is False

def test_answerable_case_accepts_primary_and_supporting_citations() -> None:
    primary_chunk = DocumentChunk(
        chunk_id="primary-chunk",
        document_id="doc-1",
        source="wordpress",
        source_id="1",
        title="Primary source",
        url="https://example.com/primary",
        content_type="page",
        text="Primary answer-bearing evidence.",
        sequence=0,
    )
    supporting_chunk = DocumentChunk(
        chunk_id="supporting-chunk",
        document_id="doc-2",
        source="wordpress",
        source_id="2",
        title="Supporting source",
        url="https://example.com/supporting",
        content_type="page",
        text="Additional supporting evidence.",
        sequence=0,
    )

    case = EvaluationCase(
        id="answerable-supporting-citation",
        category="exact_answer",
        query="What is the answer?",
        retrieval=RetrievalExpectation(
            relevant_sources=[
                GoldSource(
                    document_id="doc-1",
                    title="Primary source",
                    chunk_id="primary-chunk",
                    role="primary",
                ),
                GoldSource(
                    document_id="doc-2",
                    title="Supporting source",
                    chunk_id="supporting-chunk",
                    role="supporting",
                ),
            ]
        ),
        answer=AnswerExpectation(
            expected_sufficient_evidence=True,
            required_points=["Explain the answer."],
        ),
    )

    answer = GeneratedAnswer(
        answer="Supported answer. [S1] [S2]",
        sources=(
            ContextSource(
                citation_id="S1",
                chunk=primary_chunk,
                score=0.9,
            ),
            ContextSource(
                citation_id="S2",
                chunk=supporting_chunk,
                score=0.8,
            ),
        ),
        sufficient_evidence=True,
    )

    result = evaluate_answer_case(
        case,
        answer,
    )

    assert result.citation_behavior_correct is True
    assert result.primary_citation_present is True
    assert result.unacceptable_citation_chunk_ids == ()
    assert result.passed is True