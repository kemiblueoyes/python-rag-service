from dataclasses import dataclass

from rag_service.evaluation.models import EvaluationCase
from rag_service.generation.models import GeneratedAnswer


@dataclass(frozen=True, slots=True)
class AnswerEvaluationResult:
    """Deterministic answer checks for one evaluation case."""

    case_id: str
    query: str
    expected_sufficient_evidence: bool
    actual_sufficient_evidence: bool
    sufficiency_correct: bool
    cited_chunk_ids: tuple[str, ...]
    unacceptable_citation_chunk_ids: tuple[str, ...]
    citation_behavior_correct: bool
    required_points: tuple[str, ...]
    passed: bool
    primary_citation_present: bool


def evaluate_answer_case(
    case: EvaluationCase,
    answer: GeneratedAnswer,
) -> AnswerEvaluationResult:
    """Evaluate deterministic answer behavior against gold expectations."""

    expectation = case.answer

    if expectation is None:
        raise ValueError(
            f"Evaluation case {case.id!r} has no answer expectation."
        )

    cited_chunk_ids = tuple(
        source.chunk.chunk_id
        for source in answer.sources
    )

    acceptable_chunk_ids = set(
        source.chunk_id
        for source in case.retrieval.relevant_sources
        if source.chunk_id is not None
    )

    primary_chunk_ids = {
        source.chunk_id
        for source in case.retrieval.relevant_sources
        if source.role == "primary"
        and source.chunk_id is not None
    }

    primary_citation_present = any(
        chunk_id in primary_chunk_ids
        for chunk_id in cited_chunk_ids
    )

    unacceptable_citation_chunk_ids = tuple(
        chunk_id
        for chunk_id in cited_chunk_ids
        if chunk_id not in acceptable_chunk_ids
    )

    sufficiency_correct = (
        answer.sufficient_evidence
        == expectation.expected_sufficient_evidence
    )

    if expectation.expected_sufficient_evidence:
        citation_behavior_correct = (
            bool(cited_chunk_ids)
            and not unacceptable_citation_chunk_ids
            and primary_citation_present
        )
    else:
        citation_behavior_correct = not cited_chunk_ids

    passed = (
        sufficiency_correct
        and citation_behavior_correct
    )

    return AnswerEvaluationResult(
        case_id=case.id,
        query=case.query,
        expected_sufficient_evidence=(
            expectation.expected_sufficient_evidence
        ),
        actual_sufficient_evidence=answer.sufficient_evidence,
        sufficiency_correct=sufficiency_correct,
        cited_chunk_ids=cited_chunk_ids,
        unacceptable_citation_chunk_ids=(
            unacceptable_citation_chunk_ids
        ),
        citation_behavior_correct=citation_behavior_correct,
        required_points=tuple(expectation.required_points),
        passed=passed,
        primary_citation_present=primary_citation_present,
    )