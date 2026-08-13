from rag_service.embeddings.base import EmbeddingProvider
from rag_service.retrieval.models import (
    RetrievalRequest,
    RetrievalResult,
)
from rag_service.vectorstores.base import SearchResult, VectorStore


class RetrievalService:
    """Shared semantic retrieval pipeline used by search and answer generation."""

    _SUPPORTED_FILTERS = frozenset(
        {
            "document_id",
            "source",
            "source_id",
            "content_type",
        }
    )

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        min_score: float = 0.50,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._min_score = min_score

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalResult]:
        self._validate_request(request)

        query_vector = self._embedding_provider.embed_query(request.query.strip())

        search_results = self._vector_store.search(
            query_vector=query_vector,
            limit=request.limit,
            filters=request.filters or None,
        )

        search_results = self._deduplicate_results(search_results)
        search_results = self._filter_weak_results(search_results)

        return [
            RetrievalResult(
                chunk=result.chunk,
                score=result.score,
            )
            for result in search_results
        ]

    def _filter_weak_results(
        self,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        return [
            result
            for result in results
            if result.score >= self._min_score
        ]

    @classmethod
    def _validate_request(cls, request: RetrievalRequest) -> None:
        if not request.query.strip():
            raise ValueError("Query must not be empty.")

        if request.limit < 1:
            raise ValueError("Retrieval limit must be at least 1.")

        cls._validate_filters(request.filters)

    @classmethod
    def _validate_filters(cls, filters: dict[str, object]) -> None:
        unsupported = sorted(set(filters) - cls._SUPPORTED_FILTERS)

        if unsupported:
            names = ", ".join(unsupported)
            raise ValueError(f"Unsupported retrieval filter(s): {names}")

        for key, value in filters.items():
            if isinstance(value, str):
                if not value.strip():
                    raise ValueError(f"Filter {key!r} must not be empty.")
                continue

            if isinstance(value, (list, tuple, set, frozenset)):
                if not value:
                    raise ValueError(f"Filter {key!r} must not be empty.")

                if not all(
                    isinstance(item, str) and item.strip()
                    for item in value
                ):
                    raise ValueError(
                        f"Filter {key!r} must contain only non-empty strings."
                    )
                continue

            raise ValueError(
                f"Filter {key!r} must be a string or collection of strings."
            )

    @staticmethod
    def _deduplicate_results(
        results: list[SearchResult],
    ) -> list[SearchResult]:
        seen_chunk_ids: set[str] = set()
        unique_results: list[SearchResult] = []

        for result in results:
            if result.chunk.chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(result.chunk.chunk_id)
            unique_results.append(result)

        return unique_results