from collections.abc import Sequence
from typing import Any

import pytest

from rag_service.indexing.change_detection import DocumentChanges
from rag_service.indexing.vector_index import sync_vector_index
from rag_service.models.canonical_document import CanonicalDocument
from rag_service.models.chunk import DocumentChunk
from rag_service.vectorstores import SearchResult, VectorRecord


def _document(source_id: str) -> CanonicalDocument:
    return CanonicalDocument(
        document_id=f"wordpress:page:{source_id}",
        source="wordpress",
        source_id=source_id,
        title=f"Page {source_id}",
        url=f"https://example.test/{source_id}",
        body=f"<p>Content {source_id}</p>",
        content_type="page",
    )


def _chunk(document: CanonicalDocument) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"{document.document_id}:chunk:0",
        document_id=document.document_id,
        source=document.source,
        source_id=document.source_id,
        title=document.title,
        url=document.url,
        content_type=document.content_type,
        text=f"Chunk {document.source_id}",
        sequence=0,
    )


class RecordingEmbeddingProvider:
    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(texts)
        return [[float(index), 0.5] for index, _text in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        raise AssertionError("Index synchronization must not embed queries.")


class RecordingVectorStore:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.upserted: list[VectorRecord] = []

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        self.upserted.extend(records)

    def search(
        self,
        query_vector: list[float],
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        raise AssertionError("Index synchronization must not search.")

    def delete(self, document_id: str) -> None:
        self.deleted.append(document_id)


def test_incremental_sync_indexes_changes_and_removes_stale_documents() -> None:
    new = _document("new")
    updated = _document("updated")
    unchanged = _document("unchanged")
    removed = _document("removed")
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore()

    stats = sync_vector_index(
        DocumentChanges(
            new=[new],
            updated=[updated],
            unchanged=[unchanged],
            removed=[removed],
        ),
        [_chunk(new), _chunk(updated), _chunk(unchanged)],
        provider,
        store,
        batch_size=1,
    )

    assert provider.batches == [["Chunk new"], ["Chunk updated"]]
    assert store.deleted == [updated.document_id, removed.document_id]
    assert [record.chunk.document_id for record in store.upserted] == [
        new.document_id,
        updated.document_id,
    ]
    assert stats.documents_indexed == 2
    assert stats.documents_deleted == 2
    assert stats.chunks_indexed == 2


def test_rebuild_indexes_unchanged_documents_too() -> None:
    unchanged = _document("unchanged")
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore()

    sync_vector_index(
        DocumentChanges(new=[], updated=[], unchanged=[unchanged], removed=[]),
        [_chunk(unchanged)],
        provider,
        store,
        rebuild=True,
    )

    assert provider.batches == [["Chunk unchanged"]]
    assert store.deleted == [unchanged.document_id]
    assert [record.chunk.document_id for record in store.upserted] == [
        unchanged.document_id
    ]


class WrongCountProvider(RecordingEmbeddingProvider):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return []


def test_stops_before_deletion_when_embedding_count_is_wrong() -> None:
    updated = _document("updated")
    store = RecordingVectorStore()

    with pytest.raises(RuntimeError, match="different number of vectors"):
        sync_vector_index(
            DocumentChanges(new=[], updated=[updated], unchanged=[], removed=[]),
            [_chunk(updated)],
            WrongCountProvider(),
            store,
        )

    assert store.deleted == []
