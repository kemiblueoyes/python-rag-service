import argparse
import json
from pathlib import Path

from rag_service.config import settings
from rag_service.connectors.wordpress.client import WordPressClient
from rag_service.connectors.wordpress.connector import WordPressConnector
from rag_service.connectors.wordpress.content_policy import (
    build_wordpress_block_preserver,
)
from rag_service.indexing.change_detection import (
    DocumentChanges,
    detect_document_changes,
)
from rag_service.models.canonical_document import CanonicalDocument
from rag_service.models.chunk import DocumentChunk
from rag_service.processing.pipeline import process_documents
from rag_service.profiles.wordpress import get_wordpress_profile


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
) -> DocumentChanges:
    """Retrieve WordPress content, detect changes, and generate chunks."""

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

    _write_models(output_path, current_documents)

    if chunk_output_path is not None:
        chunks = process_documents(
            current_documents,
            preserve_block=build_wordpress_block_preserver(
                profile.preserved_block_classes
            ),
        )
        _write_models(chunk_output_path, chunks)

    return changes


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

    args = parser.parse_args()
    changes = run(args.output, args.chunks_output)

    current_count = len(changes.new) + len(changes.updated) + len(changes.unchanged)

    print(f"Wrote {current_count} canonical documents to {args.output}")
    print(f"Wrote retrieval-ready chunks to {args.chunks_output}")
    print(f"New: {len(changes.new)}")
    print(f"Updated: {len(changes.updated)}")
    print(f"Unchanged: {len(changes.unchanged)}")
    print(f"Removed or unpublished: {len(changes.removed)}")


if __name__ == "__main__":
    main()
