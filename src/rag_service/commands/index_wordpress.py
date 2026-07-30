import argparse
import json
from pathlib import Path

from rag_service.config import settings
from rag_service.connectors.wordpress.client import WordPressClient
from rag_service.connectors.wordpress.connector import WordPressConnector


def run(output_path: Path) -> int:
    """Retrieve WordPress content and write canonical documents to JSON."""

    if not settings.wordpress_base_url:
        raise ValueError(
            "WORDPRESS_BASE_URL must be configured before indexing."
        )

    client = WordPressClient(
        base_url=settings.wordpress_base_url,
        api_path=settings.wordpress_api_path,
        timeout=settings.wordpress_request_timeout,
        page_size=settings.wordpress_page_size,
    )

    try:
        connector = WordPressConnector(client)
        documents = connector.fetch_documents()
    finally:
        client.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            [
                document.model_dump(mode="json")
                for document in documents
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return len(documents)


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
    document_count = run(args.output)

    print(
        f"Wrote {document_count} canonical documents "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()