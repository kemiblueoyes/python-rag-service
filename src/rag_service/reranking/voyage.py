from collections.abc import Sequence
from typing import Protocol, cast

from rag_service.vectorstores.base import SearchResult


class _RerankingResult(Protocol):
    index: int
    relevance_score: float


class _RerankingResponse(Protocol):
    @property
    def results(self) -> Sequence[_RerankingResult]: ...


class _VoyageClient(Protocol):
    def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        model: str,
        top_k: int | None = None,
        truncation: bool = True,
    ) -> _RerankingResponse: ...


class VoyageReranker:
    """Voyage AI adapter for retrieval reranking."""

    def __init__(
        self,
        *,
        model: str = "rerank-2.5",
        api_key: str | None = None,
        client: _VoyageClient | None = None,
    ) -> None:
        if client is None:
            from voyageai.client import Client

            client = cast(
                _VoyageClient,
                Client(api_key=api_key),
            )

        self._client = client
        self._model = model

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        *,
        limit: int,
    ) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("Query must not be empty.")

        if limit < 1:
            raise ValueError("Rerank limit must be at least 1.")

        if not results:
            return []

        documents = [
            self._document_for_reranking(result)
            for result in results
        ]

        response = self._client.rerank(
            query.strip(),
            documents,
            model=self._model,
            top_k=min(limit, len(results)),
        )

        reranked: list[SearchResult] = []

        for item in response.results:
            if item.index < 0 or item.index >= len(results):
                raise RuntimeError(
                    "Voyage returned an invalid candidate index."
                )

            candidate = results[item.index]

            reranked.append(
                SearchResult(
                    chunk=candidate.chunk,
                    score=float(item.relevance_score),
                )
            )

        return reranked

    @staticmethod
    def _document_for_reranking(
        result: SearchResult,
    ) -> str:
        heading = (
            " > ".join(result.chunk.heading_path)
            or "(none)"
        )

        return (
            f"Title: {result.chunk.title}\n"
            f"Heading: {heading}\n"
            f"Content:\n{result.chunk.text}"
        )