import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from rag_service.config import settings
from rag_service.connectors.wordpress.client import WordPressClient
from rag_service.connectors.wordpress.connector import WordPressConnector
from rag_service.connectors.wordpress.content_policy import (
    build_wordpress_block_preserver,
)
from rag_service.embeddings import EmbeddingProvider, create_embedding_provider
from rag_service.indexing.change_detection import (
    DocumentChanges,
    detect_document_changes,
)
from rag_service.indexing.vector_index import VectorIndexStats, sync_vector_index
from rag_service.models.canonical_document import CanonicalDocument
from rag_service.models.chunk import DocumentChunk
from rag_service.processing.pipeline import process_documents
from rag_service.profiles.wordpress import get_wordpress_profile
from rag_service.vectorstores import VectorStore, create_vector_store


@dataclass(frozen=True, slots=True)
class WordPressIndexResult:
    changes: DocumentChanges
    vector_index: VectorIndexStats | None


def _load_previous_documents(
    output_path: Path,
) -> list[CanonicalDocument]:
    """Load canonical documents saved by the previous indexing run."""

    if not output_path.exists():
        return []

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    if not isinstance(payload, list):
        raise ValueError(f"Expected a document list in {output_path}")

    return [CanonicalDocument.model_validate(item) for item in payload]


def _write_models(
    output_path: Path,
    models: list[CanonicalDocument] | list[DocumentChunk],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            [model.model_dump(mode="json") for model in models],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def run(
    output_path: Path,
    chunk_output_path: Path | None = None,
    *,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: VectorStore | None = None,
    rebuild_vector_index: bool = False,
    embedding_batch_size: int = 128,
) -> WordPressIndexResult:
    """Retrieve WordPress content and update its retrieval artifacts."""

    if not settings.wordpress_base_url:
        raise ValueError("WORDPRESS_BASE_URL must be configured before indexing.")

    previous_documents = _load_previous_documents(output_path)
    profile = get_wordpress_profile(settings.wordpress_profile)

    client = WordPressClient(
        base_url=settings.wordpress_base_url,
        api_path=settings.wordpress_api_path,
        timeout=settings.wordpress_request_timeout,
        page_size=settings.wordpress_page_size,
        collections=settings.wordpress_collections,
    )

    try:
        connector = WordPressConnector(
            client,
            profile=profile,
        )
        current_documents = connector.fetch_documents()
    finally:
        client.close()

    changes = detect_document_changes(
        current_documents=current_documents,
        previous_documents=previous_documents,
    )

    should_sync_vectors = embedding_provider is not None or vector_store is not None
    if (embedding_provider is None) != (vector_store is None):
        raise ValueError(
            "Embedding provider and vector store must be supplied together."
        )

    chunks: list[DocumentChunk] = []
    if chunk_output_path is not None or should_sync_vectors:
        chunks = process_documents(
            current_documents,
            preserve_block=build_wordpress_block_preserver(
                profile.preserved_block_classes
            ),
            excluded_section_headings=(
                profile.excluded_section_headings
            ),
        )

    vector_index_stats = None
    if embedding_provider is not None and vector_store is not None:
        vector_index_stats = sync_vector_index(
            changes,
            chunks,
            embedding_provider,
            vector_store,
            batch_size=embedding_batch_size,
            rebuild=rebuild_vector_index,
        )

    # The snapshot represents the last successfully synchronized index.
    _write_models(output_path, current_documents)
    if chunk_output_path is not None:
        _write_models(chunk_output_path, chunks)

    return WordPressIndexResult(
        changes=changes,
        vector_index=vector_index_stats,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve and map WordPress content.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/wordpress-documents.json"),
        help="Destination for the canonical document JSON.",
    )
    parser.add_argument(
        "--chunks-output",
        type=Path,
        default=Path("data/wordpress-chunks.json"),
        help="Destination for the retrieval-ready chunk JSON.",
    )
    parser.add_argument(
        "--rebuild-vector-index",
        action="store_true",
        help="Re-embed and replace every current document in the vector index.",
    )

    args = parser.parse_args()
    result = run(
        args.output,
        args.chunks_output,
        embedding_provider=create_embedding_provider(settings),
        vector_store=create_vector_store(settings),
        rebuild_vector_index=args.rebuild_vector_index,
        embedding_batch_size=settings.embedding_batch_size,
    )
    changes = result.changes

    current_count = len(changes.new) + len(changes.updated) + len(changes.unchanged)

    print(f"Wrote {current_count} canonical documents to {args.output}")
    print(f"Wrote retrieval-ready chunks to {args.chunks_output}")
    print(f"New: {len(changes.new)}")
    print(f"Updated: {len(changes.updated)}")
    print(f"Unchanged: {len(changes.unchanged)}")
    print(f"Removed or unpublished: {len(changes.removed)}")
    if result.vector_index is not None:
        print(
            "Vector index synchronized: "
            f"{result.vector_index.documents_indexed} documents and "
            f"{result.vector_index.chunks_indexed} chunks indexed; "
            f"{result.vector_index.documents_deleted} documents cleared."
        )


if __name__ == "__main__":
    main()
