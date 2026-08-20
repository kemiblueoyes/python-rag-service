from collections.abc import Sequence
from dataclasses import dataclass

from rag_service.evaluation.models import (
    EvaluationCase,
    GoldSource,
)
from rag_service.retrieval.models import RetrievalResult

# Note that k = EVALUATION_DEPTH 
# If k = 5, for each evaluation query, judge only the top 5 retrieved chunks
# k has nothing to do with "top k"

@dataclass(frozen=True, slots=True)
class RetrievalEvaluationResult:
    """Retrieval metrics for one evaluation case."""

    case_id: str
    query: str
    expected_empty: bool
    retrieved_count: int
    relevant_retrieved_count: int
    # Did at least one primary, answer-bearing result appear
    # within the top X retrieved chunks?
    hit_at_k: bool
    # What proportion of the results evaluated were relevant?
    precision_at_k: float
    # What proportion of all known relevant sources did we retrieve?
    recall_at_k: float
    # How high did the first correct result appear? 
    # Uses reciprocal rank formula (1/rank). For example:
    # rank 1 → 1.000
    # rank 2 → 0.500
    # rank 3 → 0.333
    # rank 4 → 0.250
    # rank 5 → 0.200
    # etc.
    reciprocal_rank: float
    # Did retrieval correctly return nothing for an unanswerable question?
    empty_result_correct: bool | None


def _matches_gold_source(
    result: RetrievalResult,
    gold_source: GoldSource,
) -> bool:
    """Return whether a retrieved chunk matches a gold source."""

    chunk = result.chunk

    if gold_source.chunk_id is not None:
        return chunk.chunk_id == gold_source.chunk_id

    return (
        chunk.document_id == gold_source.document_id
        and chunk.heading_path == gold_source.heading_path
    )


def evaluate_retrieval_case(
    case: EvaluationCase,
    results: Sequence[RetrievalResult],
    *,
    k: int,
) -> RetrievalEvaluationResult:
    """Evaluate ranked retrieval results for one gold test case."""

    if k < 1:
        raise ValueError("k must be at least 1.")

    ranked_results = list(results[:k])

    if case.retrieval.expect_empty:
        return RetrievalEvaluationResult(
            case_id=case.id,
            query=case.query,
            expected_empty=True,
            retrieved_count=len(ranked_results),
            relevant_retrieved_count=0,
            hit_at_k=False,
            precision_at_k=0.0,
            recall_at_k=0.0,
            reciprocal_rank=0.0,
            empty_result_correct=not ranked_results,
        )

    gold_sources = case.retrieval.relevant_sources

    matched_gold_indexes: set[int] = set()
    relevant_result_ranks: list[int] = []
    primary_result_ranks: list[int] = []

    for rank, result in enumerate(ranked_results, start=1):
        for gold_index, gold_source in enumerate(gold_sources):
            if gold_index in matched_gold_indexes:
                continue

            if _matches_gold_source(result, gold_source):
                matched_gold_indexes.add(gold_index)
                relevant_result_ranks.append(rank)

                if gold_source.role == "primary":
                    primary_result_ranks.append(rank)

                break

    relevant_count = len(relevant_result_ranks)

    precision_at_k = relevant_count / k
    recall_at_k = relevant_count / len(gold_sources)

    reciprocal_rank = (
        1.0 / primary_result_ranks[0]
        if primary_result_ranks
        else 0.0
    )

    return RetrievalEvaluationResult(
        case_id=case.id,
        query=case.query,
        expected_empty=False,
        retrieved_count=len(ranked_results),
        relevant_retrieved_count=relevant_count,
        hit_at_k=bool(primary_result_ranks),
        precision_at_k=precision_at_k,
        recall_at_k=recall_at_k,
        reciprocal_rank=reciprocal_rank,
        empty_result_correct=None,
    )

@dataclass(frozen=True, slots=True)
class RetrievalEvaluationSummary:
    """Aggregate retrieval metrics across an evaluation dataset."""

    total_cases: int
    answerable_cases: int
    unanswerable_cases: int

    hit_rate_at_k: float
    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_reciprocal_rank: float

    unanswerable_accuracy: float
    overall_success_rate: float


def summarize_retrieval_evaluations(
    evaluations: Sequence[RetrievalEvaluationResult],
) -> RetrievalEvaluationSummary:
    """Calculate aggregate metrics across retrieval evaluations."""

    if not evaluations:
        raise ValueError(
            "At least one retrieval evaluation is required."
        )

    answerable = [
        evaluation
        for evaluation in evaluations
        if not evaluation.expected_empty
    ]

    unanswerable = [
        evaluation
        for evaluation in evaluations
        if evaluation.expected_empty
    ]

    answerable_count = len(answerable)
    unanswerable_count = len(unanswerable)

    hit_rate = (
        sum(
            evaluation.hit_at_k
            for evaluation in answerable
        )
        / answerable_count
        if answerable_count
        else 0.0
    )

    mean_precision = (
        sum(
            evaluation.precision_at_k
            for evaluation in answerable
        )
        / answerable_count
        if answerable_count
        else 0.0
    )

    mean_recall = (
        sum(
            evaluation.recall_at_k
            for evaluation in answerable
        )
        / answerable_count
        if answerable_count
        else 0.0
    )

    mean_reciprocal_rank = (
        sum(
            evaluation.reciprocal_rank
            for evaluation in answerable
        )
        / answerable_count
        if answerable_count
        else 0.0
    )

    correct_empty = sum(
        evaluation.empty_result_correct is True
        for evaluation in unanswerable
    )

    unanswerable_accuracy = (
        correct_empty / unanswerable_count
        if unanswerable_count
        else 0.0
    )

    successful_cases = (
        sum(
            evaluation.hit_at_k
            for evaluation in answerable
        )
        + correct_empty
    )

    overall_success_rate = (
        successful_cases / len(evaluations)
    )

    return RetrievalEvaluationSummary(
        total_cases=len(evaluations),
        answerable_cases=answerable_count,
        unanswerable_cases=unanswerable_count,
        hit_rate_at_k=hit_rate,
        mean_precision_at_k=mean_precision,
        mean_recall_at_k=mean_recall,
        mean_reciprocal_rank=mean_reciprocal_rank,
        unanswerable_accuracy=unanswerable_accuracy,
        overall_success_rate=overall_success_rate,
    )