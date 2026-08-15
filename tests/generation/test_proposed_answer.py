import pytest
from pydantic import ValidationError

from rag_service.generation.models import ProposedAnswer


def test_proposed_answer_accepts_grounded_answer() -> None:
    answer = ProposedAnswer(
        answer=(
            "Semantic search compares meaning rather than exact "
            "keywords [S1]."
        ),
        citation_ids=["S1"],
        sufficient_evidence=True,
    )

    assert answer.answer.endswith("[S1].")
    assert answer.citation_ids == ["S1"]
    assert answer.sufficient_evidence is True


def test_proposed_answer_preserves_citation_order() -> None:
    answer = ProposedAnswer(
        answer=(
            "Retrieval finds relevant content [S2]. "
            "Chunking prepares that content for retrieval [S1]."
        ),
        citation_ids=["S2", "S1"],
        sufficient_evidence=True,
    )

    assert answer.citation_ids == ["S2", "S1"]


def test_proposed_answer_accepts_insufficient_evidence() -> None:
    answer = ProposedAnswer(
        answer=(
            "The available sources do not contain enough information "
            "to answer this question."
        ),
        citation_ids=[],
        sufficient_evidence=False,
    )

    assert answer.citation_ids == []
    assert answer.sufficient_evidence is False


@pytest.mark.parametrize("answer", ["", " ", "\n"])
def test_proposed_answer_rejects_empty_answer(
    answer: str,
) -> None:
    with pytest.raises(
        ValidationError,
        match="answer must not be empty",
    ):
        ProposedAnswer(
            answer=answer,
            citation_ids=[],
            sufficient_evidence=False,
        )


@pytest.mark.parametrize(
    "citation_id",
    [
        "S0",
        "S01",
        "s1",
        "source1",
        "1",
        "",
    ],
)
def test_proposed_answer_rejects_invalid_citation_id(
    citation_id: str,
) -> None:
    with pytest.raises(
        ValidationError,
        match="citation IDs must use the format",
    ):
        ProposedAnswer(
            answer="Supported answer.",
            citation_ids=[citation_id],
            sufficient_evidence=True,
        )


def test_proposed_answer_rejects_duplicate_citation_ids() -> None:
    with pytest.raises(
        ValidationError,
        match="citation IDs must not contain duplicates",
    ):
        ProposedAnswer(
            answer="Supported answer [S1].",
            citation_ids=["S1", "S1"],
            sufficient_evidence=True,
        )


def test_proposed_answer_requires_citation_for_sufficient_answer() -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "sufficient answers must contain at least one citation ID"
        ),
    ):
        ProposedAnswer(
            answer="An answer without a citation.",
            citation_ids=[],
            sufficient_evidence=True,
        )


def test_proposed_answer_rejects_citation_for_insufficient_answer() -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "insufficient answers must not contain citation IDs"
        ),
    ):
        ProposedAnswer(
            answer="The available sources are insufficient.",
            citation_ids=["S1"],
            sufficient_evidence=False,
        )


def test_proposed_answer_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProposedAnswer.model_validate(
            {
                "answer": "Supported answer [S1].",
                "citation_ids": ["S1"],
                "sufficient_evidence": True,
                "url": "https://example.com/invented",
            }
        )