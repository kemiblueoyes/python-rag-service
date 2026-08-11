from collections.abc import Mapping, Sequence
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.http import models

from rag_service.models.chunk import DocumentChunk
from rag_service.vectorstores.base import SearchResult, VectorRecord


class QdrantVectorStore:
    """Qdrant adapter that persists vectors and complete chunk payloads."""

    _keyword_index_fields = (
        "chunk_id",
        "document_id",
        "source",
        "source_id",
        "content_type",
    )

    def __init__(
        self,
        *,
        collection_name: str,
        vector_size: int,
        url: str | None = None,
        api_key: str | None = None,
        client: QdrantClient | None = None,
    ) -> None:
        self._client = client or QdrantClient(url=url, api_key=api_key)
        self._collection_name = collection_name
        self._vector_size = vector_size
        self._collection_ready = False

    def ensure_collection(self) -> None:
        if self._collection_ready:
            return
        if not self._client.collection_exists(self._collection_name):
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=models.VectorParams(
                    size=self._vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
        for field_name in self._keyword_index_fields:
            self._client.create_payload_index(
                collection_name=self._collection_name,
                field_name=field_name,
                field_schema=models.PayloadSchemaType.KEYWORD,
                wait=True,
            )
        self._collection_ready = True

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        if not records:
            return
        self.ensure_collection()
        points = [
            models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, record.chunk.chunk_id)),
                vector=record.vector,
                payload=record.chunk.model_dump(mode="json"),
            )
            for record in records
        ]
        self._client.upsert(
            collection_name=self._collection_name,
            points=points,
            wait=True,
        )

    def search(
        self,
        query_vector: list[float],
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        if limit < 1:
            raise ValueError("Search limit must be at least 1.")
        response = self._client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            query_filter=self._build_filter(filters),
            limit=limit,
            with_payload=True,
        )
        results: list[SearchResult] = []
        for point in response.points:
            if not isinstance(point.payload, Mapping):
                raise RuntimeError("Qdrant search result is missing its chunk payload.")
            results.append(
                SearchResult(
                    chunk=DocumentChunk.model_validate(dict(point.payload)),
                    score=float(point.score),
                )
            )
        return results

    def delete(self, document_id: str) -> None:
        self.ensure_collection()
        self._client.delete(
            collection_name=self._collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )

    @staticmethod
    def _build_filter(values: dict[str, Any] | None) -> models.Filter | None:
        if not values:
            return None
        conditions: list[models.Condition] = []
        for key, value in values.items():
            match: models.Match = (
                models.MatchAny(any=list(value))
                if isinstance(value, (list, tuple, set, frozenset))
                else models.MatchValue(value=value)
            )
            conditions.append(models.FieldCondition(key=key, match=match))
        return models.Filter(must=conditions)
