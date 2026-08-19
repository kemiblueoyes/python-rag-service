import re
from collections.abc import Sequence

from rag_service.generation.citation_validator import (
    CitationValidator,
)
from rag_service.generation.context_assembler import ContextAssembler
from rag_service.generation.language_model import LanguageModel
from rag_service.generation.models import (
    ContextSource,
    GeneratedAnswer,
)
from rag_service.generation.prompt_builder import PromptBuilder
from rag_service.retrieval.models import RetrievalResult

_CITATION_PATTERN = re.compile(r"\[(S[1-9]\d*)\]")

def _normalize_citations(
    *,
    answer: str,
    sources: tuple[ContextSource, ...],
) -> tuple[str, tuple[ContextSource, ...]]:
    """Renumber cited sources by first appearance in the final answer."""

    source_by_id = {
        source.citation_id: source
        for source in sources
    }

    ordered_ids = list(
        dict.fromkeys(
            _CITATION_PATTERN.findall(answer)
        )
    )

    citation_map = {
        citation_id: f"S{index}"
        for index, citation_id in enumerate(
            ordered_ids,
            start=1,
        )
    }

    normalized_answer = _CITATION_PATTERN.sub(
        lambda match: (
            f"[{citation_map[match.group(1)]}]"
        ),
        answer,
    )

    normalized_sources = tuple(
        ContextSource(
            citation_id=citation_map[citation_id],
            chunk=source_by_id[citation_id].chunk,
            score=source_by_id[citation_id].score,
        )
        for citation_id in ordered_ids
    )

    return normalized_answer, normalized_sources

class AnswerGenerator:
    """Generate a grounded, citation-validated answer."""

    def __init__(
        self,
        *,
        context_assembler: ContextAssembler,
        prompt_builder: PromptBuilder,
        language_model: LanguageModel,
        citation_validator: CitationValidator,
    ) -> None:
        self._context_assembler = context_assembler
        self._prompt_builder = prompt_builder
        self._language_model = language_model
        self._citation_validator = citation_validator

    def generate(
        self,
        *,
        question: str,
        results: Sequence[RetrievalResult],
    ) -> GeneratedAnswer:
        """Generate an answer from ranked retrieval results."""

        context = self._context_assembler.assemble(results)
        prompt = self._prompt_builder.build(
            question=question,
            context=context,
        )
        proposed_answer = self._language_model.generate(prompt)
        validated_answer = self._citation_validator.validate(
            answer=proposed_answer,
            context=context,
        )

        normalized_answer, cited_sources = _normalize_citations(
            answer=validated_answer.answer,
            sources=context.sources,
        )

        return GeneratedAnswer(
            answer=normalized_answer,
            sources=cited_sources,
            sufficient_evidence=(
                validated_answer.sufficient_evidence
            ),
        )