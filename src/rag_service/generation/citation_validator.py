import re

from rag_service.generation.errors import CitationValidationError
from rag_service.generation.models import (
    AssembledContext,
    ProposedAnswer,
)

_CITATION_MARKER_PATTERN = re.compile(r"\[(S[^\[\]]*)\]")
_VALID_CITATION_ID_PATTERN = re.compile(r"S[1-9]\d*")


class CitationValidator:
    """Validate citations in a proposed answer against supplied sources."""

    def validate(
        self,
        *,
        answer: ProposedAnswer,
        context: AssembledContext,
    ) -> ProposedAnswer:
        """Return the answer if all citations are valid."""

        available_ids = {
            source.citation_id
            for source in context.sources
        }
        declared_ids = set(answer.citation_ids)
        inline_markers = _CITATION_MARKER_PATTERN.findall(
            answer.answer
        )

        malformed_ids = {
            citation_id
            for citation_id in inline_markers
            if _VALID_CITATION_ID_PATTERN.fullmatch(
                citation_id
            )
            is None
        }

        if malformed_ids:
            raise CitationValidationError(
                "answer contains malformed inline citations: "
                f"{sorted(malformed_ids)}"
            )

        inline_ids = set(inline_markers)
        unknown_ids = (
            declared_ids | inline_ids
        ) - available_ids

        if unknown_ids:
            raise CitationValidationError(
                "answer cites sources that were not supplied: "
                f"{sorted(unknown_ids)}"
            )

        if inline_ids != declared_ids:
            raise CitationValidationError(
                "inline citations do not match declared citation IDs"
            )

        return answer