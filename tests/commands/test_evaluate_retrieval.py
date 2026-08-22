from rag_service.commands.evaluate_retrieval import _case_passed
from rag_service.evaluation.models import (
    EvaluationCase,
    GoldSource,
    RetrievalExpectation,
)
from rag_service.evaluation.retrieval import RetrievalEvaluationResult


def make_evaluation(
    *,
    primary_retrieved_count: int,
    hit_at_k: bool,
) -> RetrievalEvaluationResult:
    return RetrievalEvaluationResult(
        case_id="multi-section-001",
        query="Test query",
        expected_empty=False,
        retrieved_count=5,
        relevant_retrieved_count=primary_retrieved_count,
        nonrelevant_retrieved_count=0,
        unjudged_retrieved_count=0,
        hit_at_k=hit_at_k,
        primary_retrieved_count=primary_retrieved_count,
        precision_at_k=1.0,
        recall_at_k=1.0,
        reciprocal_rank=1.0 if hit_at_k else 0.0,
        empty_result_correct=None,
    )


def test_multi_section_case_requires_all_primary_sources() -> None:
    case = EvaluationCase(
        id="multi-section-001",
        category="multi_section",
        query="Test query",
        retrieval=RetrievalExpectation(
            relevant_sources=[
                GoldSource(
                    document_id="wordpress:page:1",
                    title="Test",
                    chunk_id="primary-1",
                    role="primary",
                ),
                GoldSource(
                    document_id="wordpress:page:1",
                    title="Test",
                    chunk_id="primary-2",
                    role="primary",
                ),
                GoldSource(
                    document_id="wordpress:page:1",
                    title="Test",
                    chunk_id="primary-3",
                    role="primary",
                ),
            ]
        ),
    )

    evaluation = make_evaluation(
        primary_retrieved_count=1,
        hit_at_k=True,
    )

    assert _case_passed(case, evaluation) is False


def test_multi_section_case_passes_when_all_primary_sources_retrieved() -> None:
    case = EvaluationCase(
        id="multi-section-001",
        category="multi_section",
        query="Test query",
        retrieval=RetrievalExpectation(
            relevant_sources=[
                GoldSource(
                    document_id="wordpress:page:1",
                    title="Test",
                    chunk_id="primary-1",
                    role="primary",
                ),
                GoldSource(
                    document_id="wordpress:page:1",
                    title="Test",
                    chunk_id="primary-2",
                    role="primary",
                ),
                GoldSource(
                    document_id="wordpress:page:1",
                    title="Test",
                    chunk_id="primary-3",
                    role="primary",
                ),
            ]
        ),
    )

    evaluation = make_evaluation(
        primary_retrieved_count=3,
        hit_at_k=True,
    )

    assert _case_passed(case, evaluation) is True