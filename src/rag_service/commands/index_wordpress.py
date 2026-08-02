import argparse
import json
from pathlib import Path

from rag_service.config import settings
from rag_service.connectors.wordpress.client import WordPressClient
from rag_service.connectors.wordpress.connector import WordPressConnector
from rag_service.indexing.change_detection import (
    DocumentChanges,
    detect_document_changes,
)
from rag_service.models.canonical_document import CanonicalDocument


def _load_previous_documents(
    output_path: Path,
) -> list[CanonicalDocument]:
    """Load canonical documents saved by the previous indexing run."""

    if not output_path.exists():
        return []

    payload = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    if not isinstance(payload, list):
        raise ValueError(
            f"Expected a document list in {output_path}"
        )

    return [
        CanonicalDocument.model_validate(item)
        for item in payload
    ]


def run(output_path: Path) -> DocumentChanges:
    """Retrieve WordPress content and detect changes."""

    if not settings.wordpress_base_url:
        raise ValueError(
            "WORDPRESS_BASE_URL must be configured before indexing."
        )

    previous_documents = _load_previous_documents(output_path)

    client = WordPressClient(
        base_url=settings.wordpress_base_url,
        api_path=settings.wordpress_api_path,
        timeout=settings.wordpress_request_timeout,
        page_size=settings.wordpress_page_size,
    )

    try:
        connector = WordPressConnector(client)
        current_documents = connector.fetch_documents()
    finally:
        client.close()

    changes = detect_document_changes(
        current_documents=current_documents,
        previous_documents=previous_documents,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            [
                document.model_dump(mode="json")
                for document in current_documents
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return changes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve and map WordPress content."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/wordpress-documents.json"),
        help="Destination for the canonical document JSON.",
    )

    args = parser.parse_args()
    changes = run(args.output)

    current_count = (
        len(changes.new)
        + len(changes.updated)
        + len(changes.unchanged)
    )

    print(f"Wrote {current_count} canonical documents to {args.output}")
    print(f"New: {len(changes.new)}")
    print(f"Updated: {len(changes.updated)}")
    print(f"Unchanged: {len(changes.unchanged)}")
    print(f"Removed or unpublished: {len(changes.removed)}")


if __name__ == "__main__":
    main()