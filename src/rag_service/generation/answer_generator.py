from collections.abc import Sequence

from rag_service.generation.citation_validator import (
    CitationValidator,
)
from rag_service.generation.context_assembler import ContextAssembler
from rag_service.generation.language_model import LanguageModel
from rag_service.generation.models import GeneratedAnswer
from rag_service.generation.prompt_builder import PromptBuilder
from rag_service.retrieval.models import RetrievalResult


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

        cited_ids = set(validated_answer.citation_ids)
        cited_sources = tuple(
            source
            for source in context.sources
            if source.citation_id in cited_ids
        )

        return GeneratedAnswer(
            answer=validated_answer.answer,
            sources=cited_sources,
            sufficient_evidence=(
                validated_answer.sufficient_evidence
            ),
        )