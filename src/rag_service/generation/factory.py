from rag_service.config import Settings
from rag_service.generation.answer_generator import AnswerGenerator
from rag_service.generation.citation_validator import (
    CitationValidator,
)
from rag_service.generation.context_assembler import ContextAssembler
from rag_service.generation.prompt_builder import PromptBuilder
from rag_service.generation.providers.openai import (
    OpenAILanguageModel,
    OpenAITokenCounter,
)


def create_answer_generator(settings: Settings) -> AnswerGenerator:
    """Build the configured answer-generation workflow."""

    if settings.generation_provider != "openai":
        raise ValueError(
            "Unsupported generation provider: "
            f"{settings.generation_provider!r}"
        )

    token_counter = OpenAITokenCounter(
        model=settings.generation_model,
    )
    context_assembler = ContextAssembler(
        token_counter=token_counter,
        max_context_tokens=(
            settings.generation_context_budget_tokens
        ),
    )
    language_model = OpenAILanguageModel(
        api_key=settings.openai_api_key,
        model=settings.generation_model,
        reasoning_effort=(
            settings.generation_reasoning_effort
        ),
        max_output_tokens=(
            settings.generation_max_output_tokens
        ),
    )

    return AnswerGenerator(
        context_assembler=context_assembler,
        prompt_builder=PromptBuilder(),
        language_model=language_model,
        citation_validator=CitationValidator(),
    )