import threading
from collections.abc import Callable, Sequence
from typing import cast

from rag_service.client_lifecycle import close_client
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
        self._lock = threading.Lock()
        self._closed = False

    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> list[RetrievalResult]:
        service = self._service
        if service is None:
            with self._lock:
                if self._closed:
                    raise RuntimeError("The retrieval service is closed.")
                if self._service is None:
                    self._service = create_retrieval_service(settings)
                service = self._service

        return service.retrieve(request)

    def close(self) -> None:
        """Close an initialized retrieval service and keep it closed."""

        with self._lock:
            self._closed = True
            service = self._service
            self._service = None
        if service is not None:
            service.close()


class _SingletonCache[T]:
    """Publish one value for concurrent callers.

    ``functools.lru_cache`` can run its function once per thread when
    those threads miss at the same time, and each caller keeps the
    object that call returned. A lock around construction does not fix
    that: the waiting caller must read the cache again before it
    creates anything.
    """

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._lock = threading.Lock()
        self._value: T | None = None

    def __call__(self) -> T:
        cached = self._value
        if cached is not None:
            return cached
        with self._lock:
            cached = self._value
            if cached is not None:
                return cached
            created = self._factory()
            self._value = created
            return created

    def cache_clear(self) -> None:
        with self._lock:
            self._value = None

    def pop(self) -> T | None:
        """Remove the cached value without creating a replacement."""

        with self._lock:
            cached = self._value
            self._value = None
            return cached


def _new_retrieval_service() -> RetrievalService:
    return cast(RetrievalService, _LazyRetrievalService())


_retrieval_cache = _SingletonCache(_new_retrieval_service)


def get_retrieval_service() -> RetrievalService:
    """Return the configured retrieval service used by API endpoints."""
    return _retrieval_cache()


get_retrieval_service.cache_clear = _retrieval_cache.cache_clear  # type: ignore[attr-defined]


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
        self._lock = threading.Lock()
        self._closed = False

    def generate(
        self,
        *,
        question: str,
        results: Sequence[RetrievalResult],
    ) -> GeneratedAnswer:
        generator = self._generator
        if generator is None:
            with self._lock:
                if self._closed:
                    raise RuntimeError("The answer generator is closed.")
                if self._generator is None:
                    self._generator = create_answer_generator(settings)
                generator = self._generator
        return generator.generate(question=question, results=results)

    def close(self) -> None:
        """Close an initialized answer generator and keep it closed."""

        with self._lock:
            self._closed = True
            generator = self._generator
            self._generator = None
        if generator is not None:
            generator.close()


def _new_answer_generator() -> AnswerGenerator:
    if not settings.generation_enabled:
        return cast(AnswerGenerator, _GenerationDisabled())
    return cast(AnswerGenerator, _LazyAnswerGenerator())


_answer_cache = _SingletonCache(_new_answer_generator)


def get_answer_generator() -> AnswerGenerator:
    """Return the configured answer generator used by API endpoints."""
    return _answer_cache()


get_answer_generator.cache_clear = _answer_cache.cache_clear  # type: ignore[attr-defined]


def shutdown_api_dependencies() -> None:
    """Close cached API clients and drop them from the process cache."""

    _close_cached(_retrieval_cache)
    _close_cached(_answer_cache)


def _close_cached[T](cache: _SingletonCache[T]) -> None:
    resource = cache.pop()
    if resource is not None:
        close_client(resource, operation="shutdown")
