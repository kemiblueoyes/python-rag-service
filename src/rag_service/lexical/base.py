from typing import Any, Protocol, runtime_checkable

from rag_service.vectorstores.base import SearchResult


@runtime_checkable
class LexicalRetriever(Protocol):
    """Application-facing contract for lexical retrieval."""

    def search(
        self,
        query: str,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]: ...