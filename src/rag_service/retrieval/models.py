from dataclasses import dataclass, field
from typing import Any

from rag_service.models.chunk import DocumentChunk


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    query: str
    limit: int = 5
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunk: DocumentChunk
    score: float