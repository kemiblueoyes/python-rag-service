import os
import threading
from typing import Literal

import tiktoken
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from rag_service.errors import ServiceConfigurationError
from rag_service.generation.errors import (
    LanguageModelRefusalError,
    LanguageModelResponseError,
    MissingLanguageModelAPIKeyError,
)
from rag_service.generation.models import (
    GenerationPrompt,
    ProposedAnswer,
)
from rag_service.provider_failures import language_model_exception_for

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
            raise ServiceConfigurationError(
                operation="generation",
                reason="invalid_generation_model",
                diagnostic="Set GENERATION_MODEL to a non-empty model name.",
            )

        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding_name = _MODEL_ENCODING_FALLBACKS.get(model)

            if encoding_name is None:
                raise ServiceConfigurationError(
                    operation="generation",
                    reason="unrecognized_generation_model",
                    diagnostic=(
                        "Set GENERATION_MODEL to a model this service can tokenize."
                    ),
                ) from None

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
        model: str,
        client: OpenAI | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 0,
        reasoning_effort: ReasoningEffort = "low",
        max_output_tokens: int = 1_000,
    ) -> None:
        if not model.strip():
            raise ServiceConfigurationError(
                operation="generation",
                reason="invalid_generation_model",
                diagnostic="Set GENERATION_MODEL to a non-empty model name.",
            )

        if max_output_tokens <= 0:
            raise ServiceConfigurationError(
                operation="generation",
                reason="invalid_generation_output_budget",
                diagnostic=(
                    "Set GENERATION_MAX_OUTPUT_TOKENS to an integer of at least 1."
                ),
            )

        self._client = client
        self._owns_client = client is None
        self._closed = False
        self._client_lock = threading.Lock()
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._max_output_tokens = max_output_tokens

    def close(self) -> None:
        """Close an OpenAI client this adapter constructed."""

        with self._client_lock:
            if not self._owns_client:
                return
            client = self._client
            self._client = None
            self._owns_client = False
            self._closed = True
        if client is not None:
            client.close()

    def _require_client(self) -> OpenAI:
        """Create the OpenAI client on first use."""

        if self._client is not None:
            return self._client

        with self._client_lock:
            if self._client is not None:
                return self._client
            if self._closed:
                raise RuntimeError("The language model client is closed.")
            # Preserve the SDK's environment fallback and injected-client support.
            api_key = self._api_key
            if api_key is None:
                api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise MissingLanguageModelAPIKeyError(
                    "OPENAI_API_KEY must be configured."
                )
            self._client = OpenAI(
                api_key=self._api_key,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
            return self._client

    def generate(
        self,
        prompt: GenerationPrompt,
    ) -> ProposedAnswer:
        """Generate and parse a structured proposed answer."""

        try:
            response = self._require_client().responses.parse(
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
            replacement = language_model_exception_for(exc)
            if replacement is None:
                raise
            raise replacement from None
        except ValidationError:
            raise LanguageModelResponseError(
                "OpenAI returned an invalid structured answer"
            ) from None

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