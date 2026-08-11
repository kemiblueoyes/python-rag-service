from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from rag_service.models.chunk import DocumentChunk


@dataclass(frozen=True, slots=True)
class VectorRecord:
    chunk: DocumentChunk
    vector: list[float]


@dataclass(frozen=True, slots=True)
class SearchResult:
    chunk: DocumentChunk
    score: float


@runtime_checkable
class VectorStore(Protocol):
    """Application-facing contract for the rebuildable retrieval index."""

    def upsert(self, records: Sequence[VectorRecord]) -> None: ...

    def search(
        self,
        query_vector: list[float],
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]: ...

    def delete(self, document_id: str) -> None: ...
