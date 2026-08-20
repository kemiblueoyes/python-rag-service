from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

GoldSourceRole = Literal[
    "primary",
    "supporting",
]

EvaluationCategory = Literal[
    "exact_answer",
    "multi_section",
    "synonym",
    "ambiguous",
    "unanswerable",
    "confusable",
    "updated_content",
]

FilterValue = str | list[str]


class GoldSource(BaseModel):
    """A known-relevant source used as retrieval ground truth."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    title: str
    heading_path: list[str] = Field(default_factory=list)
    chunk_id: str | None = None
    role: GoldSourceRole = "primary"


class RetrievalExpectation(BaseModel):
    """Expected retrieval behavior for one evaluation case."""

    model_config = ConfigDict(extra="forbid")

    relevant_sources: list[GoldSource] = Field(default_factory=list)
    expect_empty: bool = False

    @model_validator(mode="after")
    def validate_expected_results(self) -> Self:
        if self.expect_empty and self.relevant_sources:
            raise ValueError(
                "Cases expecting no results must not define relevant sources."
            )

        if not self.expect_empty and not self.relevant_sources:
            raise ValueError(
                "Cases expecting results must define at least one relevant source."
            )

        if (
            not self.expect_empty
            and not any(
                source.role == "primary"
                for source in self.relevant_sources
            )
        ):
            raise ValueError(
                "Cases expecting results must define at least one primary source."
            )

        source_keys = [
            (
                source.document_id,
                tuple(source.heading_path),
                source.chunk_id,
            )
            for source in self.relevant_sources
        ]

        if len(source_keys) != len(set(source_keys)):
            raise ValueError(
                "Relevant sources must not contain duplicate chunk IDs."
            )

        return self


class AnswerExpectation(BaseModel):
    """Expected answer behavior for one evaluation case."""

    model_config = ConfigDict(extra="forbid")

    expected_sufficient_evidence: bool
    acceptable_citation_chunk_ids: list[str] = Field(default_factory=list)
    required_points: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_answer_expectation(self) -> Self:
        if (
            self.expected_sufficient_evidence
            and not self.acceptable_citation_chunk_ids
        ):
            raise ValueError(
                "Sufficient answers must define acceptable citation chunks."
            )

        if (
            not self.expected_sufficient_evidence
            and self.acceptable_citation_chunk_ids
        ):
            raise ValueError(
                "Insufficient answers must not define citation chunks."
            )

        return self


class EvaluationCase(BaseModel):
    """One question and its expected retrieval and answer behavior."""

    model_config = ConfigDict(extra="forbid")

    id: str
    category: EvaluationCategory
    query: str
    filters: dict[str, FilterValue] = Field(default_factory=dict)
    retrieval: RetrievalExpectation
    answer: AnswerExpectation | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_answer_sources(self) -> Self:
        if self.answer is None:
            return self

        retrieval_chunk_ids = {
            source.chunk_id
            for source in self.retrieval.relevant_sources
        }

        answer_chunk_ids = set(
            self.answer.acceptable_citation_chunk_ids
        )

        if not answer_chunk_ids.issubset(retrieval_chunk_ids):
            raise ValueError(
                "Answer citation chunks must also be relevant "
                "retrieval sources."
            )

        return self


class EvaluationDataset(BaseModel):
    """Versioned collection of evaluation cases."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    version: str
    description: str | None = None
    cases: list[EvaluationCase]

    @model_validator(mode="after")
    def validate_case_ids(self) -> Self:
        case_ids = [
            case.id
            for case in self.cases
        ]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError(
                "Evaluation case IDs must be unique."
            )

        return self