from collections.abc import Sequence
from dataclasses import dataclass

from rag_service.evaluation.models import (
    EvaluationCase,
    GoldSource,
    NonRelevantSource,
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
    nonrelevant_retrieved_count: int
    unjudged_retrieved_count: int
    # Did at least one primary, answer-bearing result appear
    # within the top X retrieved chunks?
    hit_at_k: bool
    # How many primary, answer-bearing gold sources were retrieved?
    primary_retrieved_count: int
    # What proportion of the results evaluated were relevant?
    # None means at least one retrieved result has not been judged yet.
    precision_at_k: float | None
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


def _matches_source(
    result: RetrievalResult,
    source: GoldSource | NonRelevantSource,
) -> bool:
    """Return whether a retrieved chunk matches a judged source."""

    chunk = result.chunk

    if source.chunk_id is not None:
        return chunk.chunk_id == source.chunk_id

    return (
        chunk.document_id == source.document_id
        and chunk.heading_path == source.heading_path
    )


def evaluate_retrieval_case(
    case: EvaluationCase,
    results: Sequence[RetrievalResult],
    *,
    k: int,
) -> RetrievalEvaluationResult:
    """Evaluate ranked retrieval results for one gold test case.
    all returned results judged → calculate Precision@5
    any returned result unjudged → Precision@5 = None"""

    if k < 1:
        raise ValueError("k must be at least 1.")

    ranked_results = list(results[:k])

    nonrelevant_sources = case.retrieval.nonrelevant_sources

    if case.retrieval.expect_empty:
        nonrelevant_count = sum(
            any(
                _matches_source(result, source)
                for source in nonrelevant_sources
            )
            for result in ranked_results
        )

        unjudged_count = len(ranked_results) - nonrelevant_count

        return RetrievalEvaluationResult(
            case_id=case.id,
            query=case.query,
            expected_empty=True,
            retrieved_count=len(ranked_results),
            relevant_retrieved_count=0,
            nonrelevant_retrieved_count=nonrelevant_count,
            unjudged_retrieved_count=unjudged_count,
            hit_at_k=False,
            precision_at_k=None,
            recall_at_k=0.0,
            reciprocal_rank=0.0,
            empty_result_correct=not ranked_results,
            primary_retrieved_count=0,
        )

    gold_sources = case.retrieval.relevant_sources

    matched_gold_indexes: set[int] = set()
    relevant_result_ranks: list[int] = []
    primary_result_ranks: list[int] = []
    nonrelevant_count = 0
    unjudged_count = 0

    for rank, result in enumerate(ranked_results, start=1):
        relevant_match_found = False

        for gold_index, gold_source in enumerate(gold_sources):
            if gold_index in matched_gold_indexes:
                continue

            if _matches_source(result, gold_source):
                matched_gold_indexes.add(gold_index)
                relevant_result_ranks.append(rank)
                relevant_match_found = True

                if gold_source.role == "primary":
                    primary_result_ranks.append(rank)

                break

        if relevant_match_found:
            continue

        if any(
            _matches_source(result, source)
            for source in nonrelevant_sources
        ):
            nonrelevant_count += 1
        else:
            unjudged_count += 1

    relevant_count = len(relevant_result_ranks)

    if unjudged_count > 0:
        precision_at_k = None
    elif ranked_results:
        precision_at_k = relevant_count / len(ranked_results)
    else:
        precision_at_k = 0.0

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
        nonrelevant_retrieved_count=nonrelevant_count,
        unjudged_retrieved_count=unjudged_count,
        hit_at_k=bool(primary_result_ranks),
        precision_at_k=precision_at_k,
        recall_at_k=recall_at_k,
        reciprocal_rank=reciprocal_rank,
        empty_result_correct=None,
        primary_retrieved_count=len(primary_result_ranks),
    )

@dataclass(frozen=True, slots=True)
class RetrievalEvaluationSummary:
    """Aggregate retrieval metrics across an evaluation dataset."""

    total_cases: int
    answerable_cases: int
    unanswerable_cases: int
    hit_rate_at_k: float
    mean_precision_at_k: float | None
    mean_recall_at_k: float
    mean_reciprocal_rank: float
    unanswerable_accuracy: float
    precision_evaluable_cases: int

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
    precision_values = [
        evaluation.precision_at_k
        for evaluation in answerable
        if evaluation.precision_at_k is not None
    ]

    # So mean precision will be based only on cases whose retrieved 
    # results have actually been fully judged.
    mean_precision = (
        sum(precision_values) / len(precision_values)
        if precision_values
        else None
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

    return RetrievalEvaluationSummary(
        total_cases=len(evaluations),
        answerable_cases=answerable_count,
        unanswerable_cases=unanswerable_count,
        hit_rate_at_k=hit_rate,
        mean_precision_at_k=mean_precision,
        mean_recall_at_k=mean_recall,
        mean_reciprocal_rank=mean_reciprocal_rank,
        unanswerable_accuracy=unanswerable_accuracy,
        precision_evaluable_cases=len(precision_values),
    )