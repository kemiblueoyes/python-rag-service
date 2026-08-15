from typing import Protocol

from rag_service.generation.models import (
    GenerationPrompt,
    ProposedAnswer,
)


class LanguageModel(Protocol):
    """Generate structured answers from provider-neutral prompts."""

    def generate(
        self,
        prompt: GenerationPrompt,
    ) -> ProposedAnswer:
        """Generate a structured proposed answer."""

        ...