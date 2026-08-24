from collections.abc import Callable
from dataclasses import dataclass

from rag_service.models.canonical_document import CanonicalDocument

from .client import WordPressClient
from .mapper import WordPressMetadataMapping, map_wordpress_post
from .models import WordPressPost

WordPressDocumentEnricher = Callable[
    [list[WordPressPost], list[CanonicalDocument]],
    None,
]


@dataclass(frozen=True)
class WordPressConnectorProfile:
    """Configure site-specific WordPress mapping and enrichment behavior."""

    metadata_mappings: tuple[WordPressMetadataMapping, ...] = ()
    document_enrichers: tuple[WordPressDocumentEnricher, ...] = ()
    preserved_block_classes: frozenset[str] = frozenset()
    excluded_section_headings: frozenset[str] = frozenset()


class WordPressConnector:
    """Retrieve WordPress content and produce canonical documents."""

    def __init__(
        self,
        client: WordPressClient,
        profile: WordPressConnectorProfile | None = None,
    ) -> None:
        self.client = client
        self.profile = profile or WordPressConnectorProfile()

    def fetch_documents(self) -> list[CanonicalDocument]:
        records = self.client.fetch_all()
        documents = [
            map_wordpress_post(
                record,
                metadata_mappings=self.profile.metadata_mappings,
            )
            for record in records
        ]

        _enrich_page_relationships(records, documents)

        for enricher in self.profile.document_enrichers:
            enricher(records, documents)

        return documents


def _enrich_page_relationships(
    records: list[WordPressPost],
    documents: list[CanonicalDocument],
) -> None:
    """Add standard WordPress parent relationships after mapping."""

    pages = {record.id: record for record in records if record.type == "page"}

    page_documents = {
        int(document.source_id): document
        for document in documents
        if document.content_type == "page"
    }

    for page_id, page in pages.items():
        document = page_documents.get(page_id)

        if document is None:
            continue

        if page.parent and page.parent in pages:
            parent = pages[page.parent]

            document.metadata["parent_title"] = parent.title.rendered
            document.metadata["parent_url"] = parent.link
