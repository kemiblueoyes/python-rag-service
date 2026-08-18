from unittest.mock import MagicMock

from rag_service.config import Settings
from rag_service.generation.factory import create_answer_generator


def test_create_answer_generator_builds_configured_dependencies(
    monkeypatch,
) -> None:
    settings = Settings(
        generation_model="gpt-5.6-terra",
        generation_reasoning_effort="low",
        generation_context_budget_tokens=8_000,
        generation_max_output_tokens=1_000,
        openai_api_key="test-key",
        _env_file=None,
    )

    token_counter = MagicMock()
    context_assembler = MagicMock()
    language_model = MagicMock()
    prompt_builder = MagicMock()
    citation_validator = MagicMock()
    answer_generator = MagicMock()

    token_counter_factory = MagicMock(
        return_value=token_counter
    )
    context_assembler_factory = MagicMock(
        return_value=context_assembler
    )
    language_model_factory = MagicMock(
        return_value=language_model
    )
    prompt_builder_factory = MagicMock(
        return_value=prompt_builder
    )
    citation_validator_factory = MagicMock(
        return_value=citation_validator
    )
    answer_generator_factory = MagicMock(
        return_value=answer_generator
    )

    monkeypatch.setattr(
        "rag_service.generation.factory.OpenAITokenCounter",
        token_counter_factory,
    )
    monkeypatch.setattr(
        "rag_service.generation.factory.ContextAssembler",
        context_assembler_factory,
    )
    monkeypatch.setattr(
        "rag_service.generation.factory.OpenAILanguageModel",
        language_model_factory,
    )
    monkeypatch.setattr(
        "rag_service.generation.factory.PromptBuilder",
        prompt_builder_factory,
    )
    monkeypatch.setattr(
        "rag_service.generation.factory.CitationValidator",
        citation_validator_factory,
    )
    monkeypatch.setattr(
        "rag_service.generation.factory.AnswerGenerator",
        answer_generator_factory,
    )

    result = create_answer_generator(settings)

    assert result is answer_generator

    token_counter_factory.assert_called_once_with(
        model="gpt-5.6-terra",
    )
    context_assembler_factory.assert_called_once_with(
        token_counter=token_counter,
        max_context_tokens=8_000,
    )
    language_model_factory.assert_called_once_with(
        api_key="test-key",
        model="gpt-5.6-terra",
        reasoning_effort="low",
        max_output_tokens=1_000,
    )
    prompt_builder_factory.assert_called_once_with()
    citation_validator_factory.assert_called_once_with()
    answer_generator_factory.assert_called_once_with(
        context_assembler=context_assembler,
        prompt_builder=prompt_builder,
        language_model=language_model,
        citation_validator=citation_validator,
    )


def test_create_answer_generator_does_not_require_openai_credentials() -> None:
    settings = Settings(
        openai_api_key=None,
        _env_file=None,
    )

    generator = create_answer_generator(settings)

    assert generator is not None