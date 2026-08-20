from datetime import UTC, datetime

import pytest

from rag_service.evaluation.models import (
    EvaluationCase,
    GoldSource,
    RetrievalExpectation,
)
from rag_service.evaluation.retrieval import (
    RetrievalEvaluationResult,
    evaluate_retrieval_case,
    summarize_retrieval_evaluations,
)
from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval.models import RetrievalResult


def make_chunk(
    *,
    chunk_id: str,
    document_id: str = "wordpress:page:1",
    heading_path: list[str] | None = None,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source="wordpress",
        source_id="1",
        title="Test document",
        url="https://example.com/test",
        content_type="page",
        text="Test content.",
        heading_path=heading_path or ["Test section"],
        sequence=0,
        published_at=datetime.now(UTC),
        modified_at=datetime.now(UTC),
    )


def make_result(
    *,
    chunk_id: str,
    score: float,
    document_id: str = "wordpress:page:1",
    heading_path: list[str] | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        chunk=make_chunk(
            chunk_id=chunk_id,
            document_id=document_id,
            heading_path=heading_path,
        ),
        score=score,
    )


def make_case(
    *,
    relevant_sources: list[GoldSource],
) -> EvaluationCase:
    return EvaluationCase(
        id="test-001",
        category="exact_answer",
        query="Test query",
        retrieval=RetrievalExpectation(
            relevant_sources=relevant_sources,
        ),
    )


def test_retrieval_case_scores_relevant_result_at_rank_one() -> None:
    case = make_case(
        relevant_sources=[
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Test section"],
                chunk_id="chunk-relevant",
            )
        ]
    )

    results = [
        make_result(
            chunk_id="chunk-relevant",
            score=0.90,
        ),
        make_result(
            chunk_id="chunk-other",
            score=0.80,
        ),
    ]

    evaluation = evaluate_retrieval_case(
        case,
        results,
        k=2,
    )

    assert evaluation.hit_at_k is True
    assert evaluation.relevant_retrieved_count == 1
    assert evaluation.precision_at_k == 0.5
    assert evaluation.recall_at_k == 1.0
    assert evaluation.reciprocal_rank == 1.0


def test_retrieval_case_scores_relevant_result_at_lower_rank() -> None:
    case = make_case(
        relevant_sources=[
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Test section"],
                chunk_id="chunk-relevant",
            )
        ]
    )

    results = [
        make_result(
            chunk_id="chunk-other-1",
            score=0.90,
        ),
        make_result(
            chunk_id="chunk-relevant",
            score=0.80,
        ),
        make_result(
            chunk_id="chunk-other-2",
            score=0.70,
        ),
    ]

    evaluation = evaluate_retrieval_case(
        case,
        results,
        k=3,
    )

    assert evaluation.hit_at_k is True
    assert evaluation.precision_at_k == pytest.approx(1 / 3)
    assert evaluation.recall_at_k == 1.0
    assert evaluation.reciprocal_rank == 0.5


def test_retrieval_case_calculates_partial_recall() -> None:
    case = make_case(
        relevant_sources=[
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Section one"],
                chunk_id="chunk-1",
            ),
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Section two"],
                chunk_id="chunk-2",
            ),
        ]
    )

    results = [
        make_result(
            chunk_id="chunk-1",
            score=0.90,
        ),
        make_result(
            chunk_id="chunk-other",
            score=0.80,
        ),
    ]

    evaluation = evaluate_retrieval_case(
        case,
        results,
        k=2,
    )

    assert evaluation.relevant_retrieved_count == 1
    assert evaluation.precision_at_k == 0.5
    assert evaluation.recall_at_k == 0.5
    assert evaluation.reciprocal_rank == 1.0


def test_retrieval_case_scores_no_relevant_results() -> None:
    case = make_case(
        relevant_sources=[
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Test section"],
                chunk_id="chunk-relevant",
            )
        ]
    )

    results = [
        make_result(
            chunk_id="chunk-other",
            score=0.90,
        )
    ]

    evaluation = evaluate_retrieval_case(
        case,
        results,
        k=1,
    )

    assert evaluation.hit_at_k is False
    assert evaluation.relevant_retrieved_count == 0
    assert evaluation.precision_at_k == 0.0
    assert evaluation.recall_at_k == 0.0
    assert evaluation.reciprocal_rank == 0.0


def test_retrieval_case_matches_document_and_heading_without_chunk_id() -> None:
    case = make_case(
        relevant_sources=[
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Expected section"],
            )
        ]
    )

    results = [
        make_result(
            chunk_id="new-chunk-id",
            score=0.90,
            document_id="wordpress:page:1",
            heading_path=["Expected section"],
        )
    ]

    evaluation = evaluate_retrieval_case(
        case,
        results,
        k=1,
    )

    assert evaluation.hit_at_k is True
    assert evaluation.recall_at_k == 1.0


def test_expected_empty_case_passes_when_no_results_returned() -> None:
    case = EvaluationCase(
        id="unanswerable-001",
        category="unanswerable",
        query="Unsupported question",
        retrieval=RetrievalExpectation(
            relevant_sources=[],
            expect_empty=True,
        ),
    )

    evaluation = evaluate_retrieval_case(
        case,
        [],
        k=5,
    )

    assert evaluation.expected_empty is True
    assert evaluation.empty_result_correct is True
    assert evaluation.retrieved_count == 0


def test_expected_empty_case_fails_when_results_returned() -> None:
    case = EvaluationCase(
        id="unanswerable-001",
        category="unanswerable",
        query="Unsupported question",
        retrieval=RetrievalExpectation(
            relevant_sources=[],
            expect_empty=True,
        ),
    )

    results = [
        make_result(
            chunk_id="false-positive",
            score=0.55,
        )
    ]

    evaluation = evaluate_retrieval_case(
        case,
        results,
        k=5,
    )

    assert evaluation.expected_empty is True
    assert evaluation.empty_result_correct is False
    assert evaluation.retrieved_count == 1


def test_retrieval_case_only_evaluates_top_k_results() -> None:
    case = make_case(
        relevant_sources=[
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Test section"],
                chunk_id="chunk-relevant",
            )
        ]
    )

    results = [
        make_result(
            chunk_id="chunk-other",
            score=0.90,
        ),
        make_result(
            chunk_id="chunk-relevant",
            score=0.80,
        ),
    ]

    evaluation = evaluate_retrieval_case(
        case,
        results,
        k=1,
    )

    assert evaluation.hit_at_k is False
    assert evaluation.recall_at_k == 0.0
    assert evaluation.reciprocal_rank == 0.0


def test_retrieval_case_rejects_invalid_k() -> None:
    case = make_case(
        relevant_sources=[
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Test section"],
                chunk_id="chunk-relevant",
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="k must be at least 1",
    ):
        evaluate_retrieval_case(
            case,
            [],
            k=0,
        )

def test_summarize_retrieval_evaluations() -> None:
    evaluations = [
        RetrievalEvaluationResult(
            case_id="answerable-1",
            query="Question one",
            expected_empty=False,
            retrieved_count=5,
            relevant_retrieved_count=2,
            hit_at_k=True,
            precision_at_k=0.4,
            recall_at_k=1.0,
            reciprocal_rank=1.0,
            empty_result_correct=None,
        ),
        RetrievalEvaluationResult(
            case_id="answerable-2",
            query="Question two",
            expected_empty=False,
            retrieved_count=5,
            relevant_retrieved_count=1,
            hit_at_k=True,
            precision_at_k=0.2,
            recall_at_k=0.5,
            reciprocal_rank=0.5,
            empty_result_correct=None,
        ),
        RetrievalEvaluationResult(
            case_id="unanswerable-1",
            query="Unsupported question",
            expected_empty=True,
            retrieved_count=0,
            relevant_retrieved_count=0,
            hit_at_k=False,
            precision_at_k=0.0,
            recall_at_k=0.0,
            reciprocal_rank=0.0,
            empty_result_correct=True,
        ),
        RetrievalEvaluationResult(
            case_id="unanswerable-2",
            query="False positive question",
            expected_empty=True,
            retrieved_count=3,
            relevant_retrieved_count=0,
            hit_at_k=False,
            precision_at_k=0.0,
            recall_at_k=0.0,
            reciprocal_rank=0.0,
            empty_result_correct=False,
        ),
    ]

    summary = summarize_retrieval_evaluations(evaluations)

    assert summary.total_cases == 4
    assert summary.answerable_cases == 2
    assert summary.unanswerable_cases == 2

    assert summary.hit_rate_at_k == 1.0
    assert summary.mean_precision_at_k == pytest.approx(0.3)
    assert summary.mean_recall_at_k == pytest.approx(0.75)
    assert summary.mean_reciprocal_rank == pytest.approx(0.75)

    assert summary.unanswerable_accuracy == 0.5
    assert summary.overall_success_rate == 0.75


def test_summarize_retrieval_evaluations_rejects_empty_input() -> None:
    with pytest.raises(
        ValueError,
        match="At least one retrieval evaluation is required",
    ):
        summarize_retrieval_evaluations([])

def test_supporting_source_does_not_determine_reciprocal_rank() -> None:
    case = make_case(
        relevant_sources=[
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Summary"],
                chunk_id="supporting-chunk",
                role="supporting",
            ),
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Answer"],
                chunk_id="primary-chunk",
                role="primary",
            ),
        ]
    )

    results = [
        make_result(
            chunk_id="supporting-chunk",
            score=0.90,
        ),
        make_result(
            chunk_id="primary-chunk",
            score=0.80,
        ),
    ]

    evaluation = evaluate_retrieval_case(
        case,
        results,
        k=2,
    )

    assert evaluation.hit_at_k is True
    assert evaluation.precision_at_k == 1.0
    assert evaluation.recall_at_k == 1.0
    assert evaluation.reciprocal_rank == 0.5


def test_supporting_source_alone_does_not_count_as_hit() -> None:
    case = make_case(
        relevant_sources=[
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Summary"],
                chunk_id="supporting-chunk",
                role="supporting",
            ),
            GoldSource(
                document_id="wordpress:page:1",
                title="Test document",
                heading_path=["Answer"],
                chunk_id="primary-chunk",
                role="primary",
            ),
        ]
    )

    results = [
        make_result(
            chunk_id="supporting-chunk",
            score=0.90,
        )
    ]

    evaluation = evaluate_retrieval_case(
        case,
        results,
        k=1,
    )

    assert evaluation.hit_at_k is False
    assert evaluation.precision_at_k == 1.0
    assert evaluation.recall_at_k == 0.5
    assert evaluation.reciprocal_rank == 0.0