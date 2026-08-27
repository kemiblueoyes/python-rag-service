from typing import Protocol, runtime_checkable

from rag_service.vectorstores.base import SearchResult


@runtime_checkable
class Reranker(Protocol):
    """Application-facing contract for reranking retrieval candidates."""

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        *,
        limit: int,
    ) -> list[SearchResult]: ...