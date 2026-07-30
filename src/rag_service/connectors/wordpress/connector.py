from collections import defaultdict

from rag_service.models.document import CanonicalDocument

from .client import WordPressClient
from .mapper import map_wordpress_post
from .models import WordPressPost


class WordPressConnector:
    """Retrieve WordPress content and produce canonical documents."""

    def __init__(self, client: WordPressClient) -> None:
        self.client = client

    def fetch_documents(self) -> list[CanonicalDocument]:
        records = self.client.fetch_all()
        documents = [map_wordpress_post(record) for record in records]

        _enrich_page_relationships(records, documents)

        return documents


def _enrich_page_relationships(
    records: list[WordPressPost],
    documents: list[CanonicalDocument],
) -> None:
    """Add parent and series relationships after all pages are mapped."""

    pages = {
        record.id: record
        for record in records
        if record.type == "page"
    }

    page_documents = {
        int(document.source_id): document
        for document in documents
        if document.content_type == "page"
    }

    children_by_parent: dict[int, list[int]] = defaultdict(list)

    for page in pages.values():
        if page.parent:
            children_by_parent[page.parent].append(page.id)

    series_roots: set[int] = set()

    for page_id, page in pages.items():
        document = page_documents[page_id]

        if page.parent and page.parent in pages:
            parent = pages[page.parent]

            document.metadata["parent_title"] = parent.title.rendered
            document.metadata["parent_url"] = parent.link

        has_series_metadata = bool(
            page.acf.get("aeo_page_name")
            or page.acf.get("aeo_page_description")
        )

        if children_by_parent.get(page_id) and has_series_metadata:
            series_roots.add(page_id)

            document.document_role = "landing"
            document.metadata["page_role"] = "series_landing_page"
            document.metadata["series_name"] = (
                page.acf.get("aeo_page_name")
                or page.title.rendered
            )
            document.metadata["series_description"] = (
                page.acf.get("aeo_page_description")
                or document.metadata.get("description")
            )
            document.metadata["series_url"] = page.link

    for page_id, _page in pages.items():
        series_root_id = _find_series_root(
            page_id,
            pages,
            series_roots,
        )

        if series_root_id is None or series_root_id == page_id:
            continue

        series_root = pages[series_root_id]
        document = page_documents[page_id]

        document.metadata["page_role"] = "series_article"
        document.metadata["series_name"] = (
            series_root.acf.get("aeo_page_name")
            or series_root.title.rendered
        )
        document.metadata["series_url"] = series_root.link


def _find_series_root(
    page_id: int,
    pages: dict[int, WordPressPost],
    series_roots: set[int],
) -> int | None:
    """Find the highest series ancestor for a page."""

    current_id = page_id
    matched_roots: list[int] = []
    visited: set[int] = set()

    while current_id in pages and current_id not in visited:
        visited.add(current_id)

        if current_id in series_roots:
            matched_roots.append(current_id)

        parent_id = pages[current_id].parent

        if not parent_id:
            break

        current_id = parent_id

    return matched_roots[-1] if matched_roots else None