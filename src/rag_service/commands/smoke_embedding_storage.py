"""Smoke test the embedding and vector-store path (upsert, search, filters)."""

from dataclasses import dataclass

from rag_service.config import settings
from rag_service.embeddings import EmbeddingProvider, create_embedding_provider
from rag_service.models.chunk import DocumentChunk
from rag_service.vectorstores import (
    SearchResult,
    VectorRecord,
    VectorStore,
    create_vector_store,
)

SMOKE_DOCUMENT_ID = "smoke-test:installation-guide"
SMOKE_CHUNK_ID = f"{SMOKE_DOCUMENT_ID}:chunk:0"


@dataclass(frozen=True, slots=True)
class SmokeTestReport:
    vector_dimensions: int
    result: SearchResult
    matching_filter_results: int
    excluding_filter_results: int


def _build_test_chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id=SMOKE_CHUNK_ID,
        document_id=SMOKE_DOCUMENT_ID,
        source="smoke-test",
        source_id="installation-guide",
        title="Smoke Test Installation Guide",
        url="https://example.test/smoke-test/installation-guide",
        content_type="smoke-test",
        text="Install the project dependencies by running uv sync.",
        heading_path=["Local setup"],
        sequence=0,
        metadata={"purpose": "retrieval-smoke-test"},
    )


def run(
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    *,
    expected_dimension: int,
) -> SmokeTestReport:
    """Exercise the real embedding and vector-store path without deleting data."""

    chunk = _build_test_chunk()
    vectors = embedding_provider.embed_documents([chunk.text])
    if len(vectors) != 1:
        raise RuntimeError("Expected exactly one document embedding.")

    vector = vectors[0]
    if len(vector) != expected_dimension:
        raise RuntimeError(
            "Embedding dimension does not match configuration: "
            f"expected {expected_dimension}, received {len(vector)}."
        )

    vector_store.upsert([VectorRecord(chunk=chunk, vector=vector)])

    query_vector = embedding_provider.embed_query(
        "How do I install the project dependencies?"
    )
    if len(query_vector) != expected_dimension:
        raise RuntimeError(
            "Query embedding dimension does not match configuration: "
            f"expected {expected_dimension}, received {len(query_vector)}."
        )

    results = vector_store.search(query_vector, limit=1)
    if not results or results[0].chunk.chunk_id != SMOKE_CHUNK_ID:
        raise RuntimeError(
            "Semantic search did not return the stored smoke-test chunk."
        )

    matching_results = vector_store.search(
        query_vector,
        limit=1,
        filters={"document_id": SMOKE_DOCUMENT_ID},
    )
    if not matching_results or matching_results[0].chunk.chunk_id != SMOKE_CHUNK_ID:
        raise RuntimeError("The matching metadata filter excluded the test chunk.")

    excluding_results = vector_store.search(
        query_vector,
        limit=1,
        filters={"document_id": "smoke-test:not-present"},
    )
    if excluding_results:
        raise RuntimeError(
            "The excluding metadata filter returned an unexpected chunk."
        )

    return SmokeTestReport(
        vector_dimensions=len(vector),
        result=results[0],
        matching_filter_results=len(matching_results),
        excluding_filter_results=len(excluding_results),
    )


def main() -> None:
    collection_name = settings.qdrant_collection
    if "smoke" not in collection_name.lower() and "test" not in collection_name.lower():
        raise ValueError(
            "QDRANT_COLLECTION must identify a dedicated smoke-test collection."
        )
    if not settings.voyage_api_key:
        raise ValueError("VOYAGE_API_KEY must be configured.")
    if not settings.qdrant_api_key:
        raise ValueError("QDRANT_API_KEY must be configured for Qdrant Cloud.")

    report = run(
        create_embedding_provider(settings),
        create_vector_store(settings),
        expected_dimension=settings.embedding_dimension,
    )

    print(f"PASS: Voyage returned a {report.vector_dimensions}-dimension vector.")
    print("PASS: Qdrant stored the chunk and returned it for a related query.")
    print(f"Retrieved title: {report.result.chunk.title}")
    print(f"Retrieved text: {report.result.chunk.text}")
    print(f"Similarity score: {report.result.score:.6f}")
    print(
        "PASS: Metadata filters included the matching document "
        f"({report.matching_filter_results} result) and excluded a different one "
        f"({report.excluding_filter_results} results)."
    )
    print(f"Test data retained in Qdrant collection: {collection_name}")
    print(f"Retained document ID: {SMOKE_DOCUMENT_ID}")


if __name__ == "__main__":
    main()
