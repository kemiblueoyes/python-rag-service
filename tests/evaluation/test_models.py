import pytest
from pydantic import ValidationError

from rag_service.evaluation.models import (
    AnswerExpectation,
    EvaluationCase,
    EvaluationDataset,
    GoldSource,
    RetrievalExpectation,
)


def make_source(
    chunk_id: str = "chunk-1",
) -> GoldSource:
    return GoldSource(
        chunk_id=chunk_id,
        document_id="document-1",
        title="Test document",
        heading_path=["Test section"],
    )


def test_retrieval_expectation_accepts_relevant_sources() -> None:
    expectation = RetrievalExpectation(
        relevant_sources=[make_source()],
    )

    assert expectation.expect_empty is False
    assert expectation.relevant_sources[0].chunk_id == "chunk-1"


def test_retrieval_expectation_accepts_expected_empty_results() -> None:
    expectation = RetrievalExpectation(
        expect_empty=True,
    )

    assert expectation.relevant_sources == []


def test_retrieval_expectation_rejects_empty_sources_when_results_expected() -> None:
    with pytest.raises(
        ValidationError,
        match="must define at least one relevant source",
    ):
        RetrievalExpectation()


def test_retrieval_expectation_rejects_sources_when_empty_expected() -> None:
    with pytest.raises(
        ValidationError,
        match="must not define relevant sources",
    ):
        RetrievalExpectation(
            relevant_sources=[make_source()],
            expect_empty=True,
        )


def test_retrieval_expectation_rejects_duplicate_chunk_ids() -> None:
    with pytest.raises(
        ValidationError,
        match="duplicate chunk IDs",
    ):
        RetrievalExpectation(
            relevant_sources=[
                make_source("chunk-1"),
                make_source("chunk-1"),
            ],
        )


def test_answer_expectation_accepts_supported_answer() -> None:
    expectation = AnswerExpectation(
        expected_sufficient_evidence=True,
        acceptable_citation_chunk_ids=["chunk-1"],
        required_points=["Metadata can narrow the retrieval set."],
    )

    assert expectation.expected_sufficient_evidence is True
    assert expectation.acceptable_citation_chunk_ids == ["chunk-1"]


def test_answer_expectation_accepts_insufficient_answer() -> None:
    expectation = AnswerExpectation(
        expected_sufficient_evidence=False,
    )

    assert expectation.acceptable_citation_chunk_ids == []


def test_answer_expectation_rejects_supported_answer_without_citations() -> None:
    with pytest.raises(
        ValidationError,
        match="must define acceptable citation chunks",
    ):
        AnswerExpectation(
            expected_sufficient_evidence=True,
        )


def test_answer_expectation_rejects_citations_for_insufficient_answer() -> None:
    with pytest.raises(
        ValidationError,
        match="must not define citation chunks",
    ):
        AnswerExpectation(
            expected_sufficient_evidence=False,
            acceptable_citation_chunk_ids=["chunk-1"],
        )


def test_evaluation_case_accepts_answer_sources_from_retrieval_sources() -> None:
    case = EvaluationCase(
        id="metadata-001",
        category="exact_answer",
        query="How does metadata improve retrieval?",
        retrieval=RetrievalExpectation(
            relevant_sources=[make_source("chunk-1")],
        ),
        answer=AnswerExpectation(
            expected_sufficient_evidence=True,
            acceptable_citation_chunk_ids=["chunk-1"],
        ),
    )

    assert case.id == "metadata-001"


def test_evaluation_case_rejects_answer_source_not_relevant_to_retrieval() -> None:
    with pytest.raises(
        ValidationError,
        match="must also be relevant retrieval sources",
    ):
        EvaluationCase(
            id="metadata-001",
            category="exact_answer",
            query="How does metadata improve retrieval?",
            retrieval=RetrievalExpectation(
                relevant_sources=[make_source("chunk-1")],
            ),
            answer=AnswerExpectation(
                expected_sufficient_evidence=True,
                acceptable_citation_chunk_ids=["chunk-2"],
            ),
        )


def test_evaluation_dataset_accepts_unique_case_ids() -> None:
    case = EvaluationCase(
        id="metadata-001",
        category="exact_answer",
        query="How does metadata improve retrieval?",
        retrieval=RetrievalExpectation(
            relevant_sources=[make_source()],
        ),
    )

    dataset = EvaluationDataset(
        dataset_id="baseline",
        version="1.0",
        cases=[case],
    )

    assert len(dataset.cases) == 1


def test_evaluation_dataset_rejects_duplicate_case_ids() -> None:
    case = EvaluationCase(
        id="metadata-001",
        category="exact_answer",
        query="How does metadata improve retrieval?",
        retrieval=RetrievalExpectation(
            relevant_sources=[make_source()],
        ),
    )

    with pytest.raises(
        ValidationError,
        match="case IDs must be unique",
    ):
        EvaluationDataset(
            dataset_id="baseline",
            version="1.0",
            cases=[case, case],
        )

def test_retrieval_expectation_accepts_primary_and_supporting_sources() -> None:
    expectation = RetrievalExpectation(
        relevant_sources=[
            make_source("primary-chunk"),
            GoldSource(
                document_id="document-1",
                title="Test document",
                heading_path=["Supporting section"],
                chunk_id="supporting-chunk",
                role="supporting",
            ),
        ],
    )

    assert expectation.relevant_sources[0].role == "primary"
    assert expectation.relevant_sources[1].role == "supporting"


def test_retrieval_expectation_requires_primary_source() -> None:
    with pytest.raises(
        ValidationError,
        match="must define at least one primary source",
    ):
        RetrievalExpectation(
            relevant_sources=[
                GoldSource(
                    document_id="document-1",
                    title="Test document",
                    heading_path=["Supporting section"],
                    chunk_id="supporting-chunk",
                    role="supporting",
                )
            ],
        )