from functools import lru_cache
from typing import cast

from rag_service.config import settings
from rag_service.generation import AnswerGenerator, create_answer_generator
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


@lru_cache(maxsize=1)
def get_answer_generator() -> AnswerGenerator:
    """Return the configured answer generator used by API endpoints."""
    return create_answer_generator(settings)
