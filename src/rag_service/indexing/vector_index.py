from collections.abc import Sequence
from dataclasses import dataclass

from rag_service.embeddings import EmbeddingProvider
from rag_service.indexing.change_detection import DocumentChanges
from rag_service.models.canonical_document import CanonicalDocument
from rag_service.models.chunk import DocumentChunk
from rag_service.vectorstores import VectorRecord, VectorStore


@dataclass(frozen=True, slots=True)
class VectorIndexStats:
    documents_deleted: int
    documents_indexed: int
    chunks_indexed: int


def _unique_documents(
    documents: Sequence[CanonicalDocument],
) -> list[CanonicalDocument]:
    return list({document.document_id: document for document in documents}.values())


def sync_vector_index(
    changes: DocumentChanges,
    chunks: Sequence[DocumentChunk],
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    *,
    batch_size: int = 128,
    rebuild: bool = False,
) -> VectorIndexStats:
    """Apply detected document changes to the vector index."""

    if batch_size < 1:
        raise ValueError("Embedding batch size must be at least 1.")

    current_documents = changes.new + changes.updated + changes.unchanged
    documents_to_index = current_documents if rebuild else changes.new + changes.updated
    documents_to_delete = _unique_documents(
        (current_documents if rebuild else changes.updated) + changes.removed
    )
    document_ids_to_index = {document.document_id for document in documents_to_index}
    chunks_to_index = [
        chunk for chunk in chunks if chunk.document_id in document_ids_to_index
    ]

    record_batches: list[list[VectorRecord]] = []
    for start in range(0, len(chunks_to_index), batch_size):
        chunk_batch = chunks_to_index[start : start + batch_size]
        vectors = embedding_provider.embed_documents(
            [chunk.text for chunk in chunk_batch]
        )
        if len(vectors) != len(chunk_batch):
            raise RuntimeError(
                "Embedding provider returned a different number of vectors than texts."
            )
        record_batches.append(
            [
                VectorRecord(chunk=chunk, vector=vector)
                for chunk, vector in zip(chunk_batch, vectors, strict=True)
            ]
        )

    # Embed first so a provider failure cannot remove previously searchable chunks.
    for document in documents_to_delete:
        vector_store.delete(document.document_id)
    for records in record_batches:
        vector_store.upsert(records)

    return VectorIndexStats(
        documents_deleted=len(documents_to_delete),
        documents_indexed=len(documents_to_index),
        chunks_indexed=len(chunks_to_index),
    )
