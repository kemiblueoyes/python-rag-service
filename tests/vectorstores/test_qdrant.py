from types import SimpleNamespace
from unittest.mock import MagicMock

from qdrant_client.http import models

from rag_service.models.chunk import DocumentChunk
from rag_service.vectorstores.base import VectorRecord
from rag_service.vectorstores.qdrant import QdrantVectorStore


def _chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id="wordpress:page:1:chunk:0",
        document_id="wordpress:page:1",
        source="wordpress",
        source_id="1",
        title="Example",
        url="https://example.test/page",
        content_type="page",
        text="Useful documentation.",
        heading_path=["Guide"],
        sequence=0,
        metadata={"language": "en-US"},
    )


def test_upsert_creates_collection_and_persists_chunk_payload() -> None:
    client = MagicMock()
    client.collection_exists.return_value = False
    store = QdrantVectorStore(collection_name="chunks", vector_size=2, client=client)

    store.upsert([VectorRecord(chunk=_chunk(), vector=[0.1, 0.2])])

    client.create_collection.assert_called_once()
    assert client.create_payload_index.call_count == 5
    indexed_fields = {
        call.kwargs["field_name"] for call in client.create_payload_index.call_args_list
    }
    assert indexed_fields == {
        "chunk_id",
        "document_id",
        "source",
        "source_id",
        "content_type",
    }
    point = client.upsert.call_args.kwargs["points"][0]
    assert point.vector == [0.1, 0.2]
    assert point.payload["chunk_id"] == _chunk().chunk_id
    assert point.payload["metadata"] == {"language": "en-US"}


def test_search_returns_domain_results_and_builds_filters() -> None:
    chunk = _chunk()
    client = MagicMock()
    client.query_points.return_value = SimpleNamespace(
        points=[SimpleNamespace(payload=chunk.model_dump(mode="json"), score=0.91)]
    )
    store = QdrantVectorStore(collection_name="chunks", vector_size=2, client=client)

    results = store.search([0.1, 0.2], limit=3, filters={"content_type": "page"})

    assert results[0].chunk == chunk
    assert results[0].score == 0.91
    query_filter = client.query_points.call_args.kwargs["query_filter"]
    assert isinstance(query_filter, models.Filter)


def test_delete_uses_document_id_payload_filter() -> None:
    client = MagicMock()
    store = QdrantVectorStore(collection_name="chunks", vector_size=2, client=client)

    store.delete("wordpress:page:1")

    selector = client.delete.call_args.kwargs["points_selector"]
    condition = selector.filter.must[0]
    assert isinstance(condition, models.FieldCondition)
    assert condition.key == "document_id"
