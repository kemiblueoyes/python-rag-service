from collections.abc import Sequence
from typing import Any

import pytest

from rag_service.commands.smoke_retrieval import SMOKE_CHUNK_ID, run
from rag_service.vectorstores import SearchResult, VectorRecord


class FakeEmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        assert texts == ["Install the project dependencies by running uv sync."]
        return [[0.1, 0.2]]

    def embed_query(self, text: str) -> list[float]:
        assert text == "How do I install the project dependencies?"
        return [0.1, 0.2]


class FakeVectorStore:
    def __init__(self) -> None:
        self.record: VectorRecord | None = None

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        self.record = records[0]

    def search(
        self,
        query_vector: list[float],
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        assert query_vector == [0.1, 0.2]
        assert limit == 1
        assert self.record is not None
        if filters == {"document_id": "smoke-test:not-present"}:
            return []
        return [SearchResult(chunk=self.record.chunk, score=0.93)]

    def delete(self, document_id: str) -> None:
        raise AssertionError("The smoke test must not delete retained test data.")


def test_runs_embedding_storage_search_and_filter_checks_without_deletion() -> None:
    vector_store = FakeVectorStore()

    report = run(
        FakeEmbeddingProvider(),
        vector_store,
        expected_dimension=2,
    )

    assert vector_store.record is not None
    assert vector_store.record.chunk.chunk_id == SMOKE_CHUNK_ID
    assert report.vector_dimensions == 2
    assert report.result.score == 0.93
    assert report.matching_filter_results == 1
    assert report.excluding_filter_results == 0


class WrongDimensionProvider(FakeEmbeddingProvider):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1]]


def test_stops_when_document_embedding_dimension_is_incorrect() -> None:
    with pytest.raises(RuntimeError, match="expected 2, received 1"):
        run(
            WrongDimensionProvider(),
            FakeVectorStore(),
            expected_dimension=2,
        )
