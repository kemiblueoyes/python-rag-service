from collections.abc import Sequence
from functools import lru_cache
from typing import cast

from rag_service.config import settings
from rag_service.generation import (
    AnswerGenerator,
    GeneratedAnswer,
    create_answer_generator,
)
from rag_service.generation.errors import GenerationDisabledError
from rag_service.retrieval import (
    RetrievalRequest,
    RetrievalResult,
    RetrievalService,
    create_retrieval_service,
)


class _LazyRetrievalService:
    """Build the retrieval pipeline on first retrieve().

    FastAPI resolves endpoint dependencies before request-body
    validation, so constructing Qdrant, Voyage, and the BM25 corpus
    here would fail validation-only requests in environments that
    do not have those resources.
    """

    def __init__(self) -> None:
        self._service: RetrievalService | None = None

    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> list[RetrievalResult]:
        if self._service is None:
            self._service = create_retrieval_service(settings)

        return self._service.retrieve(request)


@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """Return the configured retrieval service used by API endpoints."""
    return cast(RetrievalService, _LazyRetrievalService())


class _GenerationDisabled:
    """Placeholder resolved before request-body validation.

    FastAPI resolves endpoint dependencies before it validates the
    body. This object keeps that resolution from building the answer
    generator or contacting a provider while generation is off.
    """

    def generate(self, **_kwargs: object) -> object:
        raise GenerationDisabledError("Answer generation is disabled.")


class _LazyAnswerGenerator:
    """Build the answer generator on first generate().

    FastAPI resolves endpoint dependencies before request-body validation.
    Building the token counter and language-model client here would turn a
    malformed request into a dependency failure.
    """

    def __init__(self) -> None:
        self._generator: AnswerGenerator | None = None

    def generate(
        self,
        *,
        question: str,
        results: Sequence[RetrievalResult],
    ) -> GeneratedAnswer:
        if self._generator is None:
            self._generator = create_answer_generator(settings)
        return self._generator.generate(question=question, results=results)


@lru_cache(maxsize=1)
def get_answer_generator() -> AnswerGenerator:
    """Return the configured answer generator used by API endpoints."""
    if not settings.generation_enabled:
        return cast(AnswerGenerator, _GenerationDisabled())

    return cast(AnswerGenerator, _LazyAnswerGenerator())
