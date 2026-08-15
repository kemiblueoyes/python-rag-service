from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from rag_service.generation.errors import (
    LanguageModelProviderError,
    LanguageModelRefusalError,
    LanguageModelResponseError,
)
from rag_service.generation.language_model import LanguageModel
from rag_service.generation.models import (
    GenerationPrompt,
    ProposedAnswer,
)
from rag_service.generation.providers.openai import (
    OpenAILanguageModel,
    OpenAITokenCounter,
)
from rag_service.generation.token_counter import TokenCounter


def test_openai_token_counter_counts_plain_text() -> None:
    counter: TokenCounter = OpenAITokenCounter(
        model="gpt-5.6-terra",
    )

    token_count = counter.count_tokens(
        "Retrieval finds relevant content."
    )

    assert token_count > 0


def test_openai_token_counter_returns_zero_for_empty_text() -> None:
    counter = OpenAITokenCounter(
        model="gpt-5.6-terra",
    )

    assert counter.count_tokens("") == 0


def test_openai_token_counter_is_deterministic() -> None:
    counter = OpenAITokenCounter(
        model="gpt-5.6-terra",
    )
    text = "The same text should produce the same token count."

    assert counter.count_tokens(text) == (
        counter.count_tokens(text)
    )


def test_openai_token_counter_handles_special_token_text() -> None:
    counter = OpenAITokenCounter(
        model="gpt-5.6-terra",
    )

    token_count = counter.count_tokens(
        "Documentation containing <|endoftext|> as an example."
    )

    assert token_count > 0


def test_openai_token_counter_rejects_empty_model() -> None:
    with pytest.raises(
        ValueError,
        match="model must not be empty",
    ):
        OpenAITokenCounter(model=" ")


@pytest.mark.parametrize(
    "model",
    [
        "definitely-not-a-real-model",
        "gpt-5.999-fake",
    ],
)
def test_openai_token_counter_rejects_unknown_model(
    model: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="tiktoken does not recognize model",
    ):
        OpenAITokenCounter(model=model)

def make_openai_language_model() -> tuple[Mock, OpenAILanguageModel]:
    """Create an OpenAI adapter with a mocked SDK client."""

    client = Mock()

    model = OpenAILanguageModel(
        client=cast(OpenAI, client),
        model="gpt-5.6-terra",
        reasoning_effort="low",
        max_output_tokens=1_000,
    )

    return client, model


def make_prompt() -> GenerationPrompt:
    """Create a provider-neutral generation prompt."""

    return GenerationPrompt(
        system_message="Use only the supplied sources.",
        user_message=(
            "Question:\nWhat is RAG?\n\n"
            "Sources:\n[SOURCE S1]\n"
            "Content:\nRAG uses retrieval.\n"
            "[END SOURCE S1]"
        ),
    )


def test_openai_language_model_returns_parsed_answer() -> None:
    client, model = make_openai_language_model()
    language_model: LanguageModel = model
    proposed_answer = ProposedAnswer(
        answer="RAG uses retrieval [S1].",
        citation_ids=["S1"],
        sufficient_evidence=True,
    )
    client.responses.parse.return_value = SimpleNamespace(
        status="completed",
        incomplete_details=None,
        output=[],
        output_parsed=proposed_answer,
    )

    result = language_model.generate(make_prompt())

    assert result is proposed_answer

    request = client.responses.parse.call_args.kwargs

    assert request["model"] == "gpt-5.6-terra"
    assert request["input"] == [
        {
            "role": "system",
            "content": "Use only the supplied sources.",
        },
        {
            "role": "user",
            "content": (
                "Question:\nWhat is RAG?\n\n"
                "Sources:\n[SOURCE S1]\n"
                "Content:\nRAG uses retrieval.\n"
                "[END SOURCE S1]"
            ),
        },
    ]
    assert request["reasoning"] == {"effort": "low"}
    assert request["max_output_tokens"] == 1_000
    assert request["text_format"] is ProposedAnswer
    assert request["store"] is False
    assert "tools" not in request


def test_openai_language_model_wraps_provider_error() -> None:
    client, model = make_openai_language_model()
    client.responses.parse.side_effect = OpenAIError(
        "provider failure"
    )

    with pytest.raises(
        LanguageModelProviderError,
        match="OpenAI answer-generation request failed",
    ):
        model.generate(make_prompt())


def test_openai_language_model_wraps_validation_error() -> None:
    client, model = make_openai_language_model()

    try:
        ProposedAnswer(
            answer="",
            citation_ids=[],
            sufficient_evidence=False,
        )
    except ValidationError as exc:
        client.responses.parse.side_effect = exc

    with pytest.raises(
        LanguageModelResponseError,
        match="OpenAI returned an invalid structured answer",
    ):
        model.generate(make_prompt())


def test_openai_language_model_rejects_incomplete_response() -> None:
    client, model = make_openai_language_model()
    client.responses.parse.return_value = SimpleNamespace(
        status="incomplete",
        incomplete_details=SimpleNamespace(
            reason="max_output_tokens"
        ),
        output=[],
        output_parsed=None,
    )

    with pytest.raises(
        LanguageModelResponseError,
        match=(
            "OpenAI returned an incomplete response: "
            "max_output_tokens"
        ),
    ):
        model.generate(make_prompt())


def test_openai_language_model_rejects_refusal() -> None:
    client, model = make_openai_language_model()
    client.responses.parse.return_value = SimpleNamespace(
        status="completed",
        incomplete_details=None,
        output=[
            SimpleNamespace(
                type="message",
                content=[
                    SimpleNamespace(
                        type="refusal",
                        refusal="Request refused.",
                    )
                ],
            )
        ],
        output_parsed=None,
    )

    with pytest.raises(
        LanguageModelRefusalError,
        match="OpenAI refused the answer-generation request",
    ):
        model.generate(make_prompt())


def test_openai_language_model_rejects_missing_parsed_answer() -> None:
    client, model = make_openai_language_model()
    client.responses.parse.return_value = SimpleNamespace(
        status="completed",
        incomplete_details=None,
        output=[],
        output_parsed=None,
    )

    with pytest.raises(
        LanguageModelResponseError,
        match="OpenAI returned no parsed answer",
    ):
        model.generate(make_prompt())


def test_openai_language_model_rejects_empty_model() -> None:
    with pytest.raises(
        ValueError,
        match="model must not be empty",
    ):
        OpenAILanguageModel(
            client=cast(OpenAI, Mock()),
            model=" ",
        )


@pytest.mark.parametrize("max_output_tokens", [0, -1])
def test_openai_language_model_rejects_invalid_output_limit(
    max_output_tokens: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_output_tokens must be greater than zero",
    ):
        OpenAILanguageModel(
            client=cast(OpenAI, Mock()),
            model="gpt-5.6-terra",
            max_output_tokens=max_output_tokens,
        )