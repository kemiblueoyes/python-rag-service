import re
from dataclasses import dataclass
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    model_validator,
)

from rag_service.models.chunk import DocumentChunk


@dataclass(frozen=True, slots=True)
class ContextSource:
    """One retrieved chunk selected as evidence for answer generation."""

    citation_id: str
    chunk: DocumentChunk
    score: float


@dataclass(frozen=True, slots=True)
class AssembledContext:
    """Ordered evidence selected for answer generation."""

    sources: tuple[ContextSource, ...]
    token_count: int

    def __post_init__(self) -> None:
        """Validate the assembled context."""

        if self.token_count < 0:
            raise ValueError("token_count must be zero or greater")

@dataclass(frozen=True, slots=True)
class GenerationPrompt:
    """Provider-neutral messages used for answer generation."""

    system_message: str
    user_message: str

class ProposedAnswer(BaseModel):
    """Structured answer proposed by the language model."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    citation_ids: list[str]
    sufficient_evidence: bool

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        """Require a nonempty answer or insufficiency explanation."""

        if not value.strip():
            raise ValueError("answer must not be empty")

        return value

    @field_validator("citation_ids")
    @classmethod
    def validate_citation_ids(
        cls,
        value: list[str],
    ) -> list[str]:
        """Require unique, structurally valid citation identifiers."""

        for citation_id in value:
            if re.fullmatch(r"S[1-9]\d*", citation_id) is None:
                raise ValueError(
                    "citation IDs must use the format S1, S2, ..."
                )

        if len(value) != len(set(value)):
            raise ValueError("citation IDs must not contain duplicates")

        return value

    @model_validator(mode="after")
    def validate_evidence_and_citations(self) -> Self:
        """Keep citation presence consistent with evidence sufficiency."""

        if self.sufficient_evidence and not self.citation_ids:
            raise ValueError(
                "sufficient answers must contain at least one citation ID"
            )

        if not self.sufficient_evidence and self.citation_ids:
            raise ValueError(
                "insufficient answers must not contain citation IDs"
            )

        return self