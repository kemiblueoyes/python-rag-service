import json
from pathlib import Path
from unittest.mock import MagicMock

from pytest import MonkeyPatch

from rag_service.commands import index_wordpress
from rag_service.connectors.wordpress.connector import WordPressConnectorProfile
from rag_service.models.canonical_document import CanonicalDocument


def test_writes_canonical_documents_and_processed_chunks(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    document = CanonicalDocument(
        document_id="wordpress:page:501",
        source="wordpress",
        source_id="501",
        title="Accordion Example",
        url="https://example.test/accordion-example/",
        body="""
            <h2 id="components">Components</h2>
            <div class="wp-block-accordion">
                <h3>Diagram title</h3>
                <p>Diagram content.</p>
            </div>
        """,
        content_type="page",
        metadata={"language": "en-US"},
    )
    monkeypatch.setattr(
        index_wordpress.settings,
        "wordpress_base_url",
        "https://example.test",
    )
    monkeypatch.setattr(
        index_wordpress.settings,
        "wordpress_collections",
        ("posts", "pages", "glossary"),
    )
    monkeypatch.setattr(
        index_wordpress.settings,
        "wordpress_profile",
        "doc_landscape",
    )
    profile = WordPressConnectorProfile(
        preserved_block_classes=frozenset({"wp-block-accordion"})
    )
    profile_resolver = MagicMock(return_value=profile)
    monkeypatch.setattr(
        index_wordpress,
        "get_wordpress_profile",
        profile_resolver,
    )
    client = MagicMock()
    client_factory = MagicMock(return_value=client)
    monkeypatch.setattr(index_wordpress, "WordPressClient", client_factory)
    monkeypatch.setattr(
        index_wordpress.WordPressConnector,
        "fetch_documents",
        lambda _connector: [document],
    )
    document_path = tmp_path / "documents.json"
    chunk_path = tmp_path / "chunks.json"

    result = index_wordpress.run(document_path, chunk_path)

    client_factory.assert_called_once_with(
        base_url="https://example.test",
        api_path="/wp-json/wp/v2",
        timeout=10.0,
        page_size=100,
        collections=("posts", "pages", "glossary"),
    )
    client.close.assert_called_once_with()
    profile_resolver.assert_called_once_with("doc_landscape")

    document_payload = json.loads(document_path.read_text(encoding="utf-8"))
    chunk_payload = json.loads(chunk_path.read_text(encoding="utf-8"))

    assert result.changes.new == [document]
    assert result.vector_index is None
    assert document_payload[0]["document_id"] == document.document_id
    assert chunk_payload[0]["document_id"] == document.document_id
    assert chunk_payload[0]["heading_path"] == ["Components"]
    assert chunk_payload[0]["block_types"] == ["html_block"]
    assert chunk_payload[0]["block_metadata"][0]["block_type"] == "html_block"
    assert "wp-block-accordion" in chunk_payload[0]["block_metadata"][0]["html"]
    assert chunk_payload[0]["anchor"] == "components"
    assert chunk_payload[0]["metadata"] == {"language": "en-US"}
