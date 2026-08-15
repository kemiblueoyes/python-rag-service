from typing import Literal

import tiktoken
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from rag_service.generation.errors import (
    LanguageModelProviderError,
    LanguageModelRefusalError,
    LanguageModelResponseError,
)
from rag_service.generation.models import (
    GenerationPrompt,
    ProposedAnswer,
)

# tiktoken maps "gpt-5" and the "gpt-5-" prefix, but not dotted
# minor versions such as "gpt-5.6-terra".
_MODEL_ENCODING_FALLBACKS = {
    "gpt-5.6-sol": "o200k_base",
    "gpt-5.6-terra": "o200k_base",
    "gpt-5.6-luna": "o200k_base",
}


class OpenAITokenCounter:
    """Count plain-text tokens using an OpenAI model's encoding."""

    def __init__(
        self,
        *,
        model: str,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")

        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError as exc:
            encoding_name = _MODEL_ENCODING_FALLBACKS.get(model)

            if encoding_name is None:
                raise ValueError(
                    f"tiktoken does not recognize model {model!r}"
                ) from exc

            self._encoding = tiktoken.get_encoding(
                encoding_name
            )

    def count_tokens(self, text: str) -> int:
        """Return the number of tokens in plain text."""

        return len(
            self._encoding.encode(
                text,
                disallowed_special=(),
            )
        )

ReasoningEffort = Literal[
    "none",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
]


class OpenAILanguageModel:
    """Generate structured answers through the OpenAI Responses API."""

    def __init__(
        self,
        *,
        client: OpenAI,
        model: str,
        reasoning_effort: ReasoningEffort = "low",
        max_output_tokens: int = 1_000,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")

        if max_output_tokens <= 0:
            raise ValueError(
                "max_output_tokens must be greater than zero"
            )

        self._client = client
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._max_output_tokens = max_output_tokens

    def generate(
        self,
        prompt: GenerationPrompt,
    ) -> ProposedAnswer:
        """Generate and parse a structured proposed answer."""

        try:
            response = self._client.responses.parse(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": prompt.system_message,
                    },
                    {
                        "role": "user",
                        "content": prompt.user_message,
                    },
                ],
                reasoning={
                    "effort": self._reasoning_effort,
                },
                max_output_tokens=self._max_output_tokens,
                text_format=ProposedAnswer,
                store=False,
            )
        except OpenAIError as exc:
            raise LanguageModelProviderError(
                "OpenAI answer-generation request failed"
            ) from exc
        except ValidationError as exc:
            raise LanguageModelResponseError(
                "OpenAI returned an invalid structured answer"
            ) from exc

        if response.status == "incomplete":
            reason = (
                response.incomplete_details.reason
                if response.incomplete_details is not None
                else "unknown"
            )
            raise LanguageModelResponseError(
                f"OpenAI returned an incomplete response: {reason}"
            )

        for output in response.output:
            if output.type != "message":
                continue

            for item in output.content:
                if item.type == "refusal":
                    raise LanguageModelRefusalError(
                        "OpenAI refused the answer-generation request"
                    )

        if response.output_parsed is None:
            raise LanguageModelResponseError(
                "OpenAI returned no parsed answer"
            )

        return response.output_parsed