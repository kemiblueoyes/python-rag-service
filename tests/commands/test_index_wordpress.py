import json
import os
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from rag_service.commands import index_wordpress
from rag_service.config import settings
from rag_service.connectors.wordpress.connector import (
    WordPressConnector,
    WordPressConnectorProfile,
)
from rag_service.indexing.change_detection import DocumentChanges
from rag_service.models.canonical_document import CanonicalDocument
from rag_service.operations import adapters


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
            <h2>Related Terms</h2>
            <p>Semantic search.</p>
        """,
        content_type="page",
        metadata={"language": "en-US"},
    )
    monkeypatch.setattr(
        settings,
        "wordpress_base_url",
        "https://example.test",
    )
    monkeypatch.setattr(
        settings,
        "wordpress_collections",
        ("posts", "pages", "glossary"),
    )
    monkeypatch.setattr(
        settings,
        "wordpress_profile",
        "doc_landscape",
    )
    profile = WordPressConnectorProfile(
        preserved_block_classes=frozenset({"wp-block-accordion"}),
        excluded_section_headings=frozenset({"Related Terms"}),
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
        WordPressConnector,
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
    assert len(chunk_payload) == 1
    assert all("Related Terms" not in chunk["heading_path"] for chunk in chunk_payload)


def _document(title: str) -> CanonicalDocument:
    return CanonicalDocument(
        document_id="wordpress:page:501",
        source="wordpress",
        source_id="501",
        title=title,
        url="https://example.test/501/",
        body=f"<p>{title}</p>",
        content_type="page",
    )


def _write_documents(path: Path, documents: list[CanonicalDocument]) -> str:
    text = json.dumps(
        [document.model_dump(mode="json") for document in documents],
        indent=2,
        ensure_ascii=False,
    )
    path.write_text(text, encoding="utf-8")
    return text


def _prepare_wordpress(
    monkeypatch: MonkeyPatch,
    documents: list[CanonicalDocument],
) -> None:
    monkeypatch.setattr(settings, "wordpress_base_url", "https://example.test")
    monkeypatch.setattr(settings, "wordpress_profile", "default")
    monkeypatch.setattr(settings, "wordpress_collections", ("pages",))
    monkeypatch.setattr(
        index_wordpress,
        "WordPressClient",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        WordPressConnector,
        "fetch_documents",
        lambda _connector: documents,
    )


def _temporary_files(directory: Path) -> list[Path]:
    return [path for path in directory.iterdir() if path.name.endswith(".tmp")]


class _Embedding:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.error is not None:
            raise self.error
        return [[0.1, 0.2] for _text in texts]

    def embed_query(self, text: str) -> list[float]:
        raise AssertionError("indexing must not embed queries")

    def close(self) -> None:
        return None


class _VectorStore:
    def upsert(self, records: object) -> None:
        return None

    def delete(self, document_id: str) -> None:
        return None

    def search(self, *_args: object, **_kwargs: object) -> list[object]:
        raise AssertionError("indexing must not search")

    def close(self) -> None:
        return None


def _fail_replace_for(
    destination: Path,
) -> Callable[[str | os.PathLike[str], str | os.PathLike[str]], None]:
    original_replace = os.replace

    def replace(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
    ) -> None:
        if Path(target) == destination:
            raise OSError(f"publication failed for {destination.name}")
        original_replace(source, target)

    return replace


def test_vector_sync_failure_leaves_both_files_unchanged(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    previous = _document("Previous title")
    document_path = tmp_path / "wordpress-documents.json"
    chunk_path = tmp_path / "wordpress-chunks.json"
    document_text = _write_documents(document_path, [previous])
    chunk_text = "[]\n"
    chunk_path.write_text(chunk_text, encoding="utf-8")
    _prepare_wordpress(monkeypatch, [_document("Updated title")])

    with pytest.raises(RuntimeError, match="voyage failed"):
        index_wordpress.run(
            document_path,
            chunk_path,
            embedding_provider=_Embedding(RuntimeError("voyage failed")),
            vector_store=_VectorStore(),
        )

    assert document_path.read_text(encoding="utf-8") == document_text
    assert chunk_path.read_text(encoding="utf-8") == chunk_text
    assert _temporary_files(tmp_path) == []


def test_failed_chunk_publication_leaves_document_checkpoint_unchanged(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    previous = _document("Previous title")
    document_path = tmp_path / "wordpress-documents.json"
    chunk_path = tmp_path / "wordpress-chunks.json"
    document_text = _write_documents(document_path, [previous])
    chunk_text = "[]\n"
    chunk_path.write_text(chunk_text, encoding="utf-8")
    _prepare_wordpress(monkeypatch, [_document("Updated title")])
    monkeypatch.setattr(
        index_wordpress.os,
        "replace",
        _fail_replace_for(chunk_path),
    )

    with pytest.raises(OSError, match="wordpress-chunks.json"):
        index_wordpress.run(
            document_path,
            chunk_path,
            embedding_provider=_Embedding(),
            vector_store=_VectorStore(),
        )

    assert document_path.read_text(encoding="utf-8") == document_text
    assert chunk_path.read_text(encoding="utf-8") == chunk_text
    assert _temporary_files(tmp_path) == []


def test_failed_document_publication_keeps_pending_changes(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    previous = _document("Previous title")
    updated = _document("Updated title")
    document_path = tmp_path / "wordpress-documents.json"
    chunk_path = tmp_path / "wordpress-chunks.json"
    document_text = _write_documents(document_path, [previous])
    chunk_path.write_text("[]\n", encoding="utf-8")
    _prepare_wordpress(monkeypatch, [updated])
    detected: list[DocumentChanges] = []
    original = index_wordpress.detect_document_changes

    def spy(
        current_documents: list[CanonicalDocument],
        previous_documents: list[CanonicalDocument],
    ) -> DocumentChanges:
        changes = original(
            current_documents=current_documents,
            previous_documents=previous_documents,
        )
        detected.append(changes)
        return changes

    monkeypatch.setattr(index_wordpress, "detect_document_changes", spy)
    monkeypatch.setattr(
        index_wordpress.os,
        "replace",
        _fail_replace_for(document_path),
    )

    for _attempt in range(2):
        with pytest.raises(OSError, match="wordpress-documents.json"):
            index_wordpress.run(
                document_path,
                chunk_path,
                embedding_provider=_Embedding(),
                vector_store=_VectorStore(),
            )

    assert json.loads(document_path.read_text(encoding="utf-8"))[0]["title"] == (
        "Previous title"
    )
    assert document_path.read_text(encoding="utf-8") == document_text
    published_chunks = json.loads(chunk_path.read_text(encoding="utf-8"))
    assert published_chunks[0]["title"] == "Updated title"
    assert _temporary_files(tmp_path) == []
    assert [item.title for item in detected[-1].updated] == ["Updated title"]
    assert detected[-1].unchanged == []
    assert detected[-1].new == []
    assert detected[-1].removed == []


def test_retry_publishes_checkpoint_and_reports_changes(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    previous = _document("Previous title")
    updated = _document("Updated title")
    document_path = tmp_path / "wordpress-documents.json"
    chunk_path = tmp_path / "wordpress-chunks.json"
    _write_documents(document_path, [previous])
    chunk_path.write_text("[]\n", encoding="utf-8")
    _prepare_wordpress(monkeypatch, [updated])
    monkeypatch.setattr(adapters, "DOCUMENT_PATH", document_path)
    monkeypatch.setattr(settings, "lexical_corpus_path", chunk_path)
    monkeypatch.setattr(
        adapters,
        "create_embedding_provider",
        lambda _settings: _Embedding(),
    )
    monkeypatch.setattr(
        adapters,
        "create_vector_store",
        lambda _settings: _VectorStore(),
    )
    original_replace = os.replace
    monkeypatch.setattr(
        index_wordpress.os,
        "replace",
        _fail_replace_for(document_path),
    )

    with pytest.raises(OSError, match="wordpress-documents.json"):
        adapters.index("failed-publication")

    monkeypatch.setattr(index_wordpress.os, "replace", original_replace)
    result = adapters.index("successful-retry")

    assert result["new"] == 0
    assert result["updated"] == 1
    assert result["unchanged"] == 0
    assert result["removed"] == 0
    assert result["changes_detected"] is True
    assert result["documents_indexed"] == 1
    assert result["documents_cleared"] == 1
    assert result["artifact_paths"] == {
        "documents": str(document_path),
        "chunks": str(chunk_path),
    }
    assert json.loads(document_path.read_text(encoding="utf-8"))[0]["title"] == (
        "Updated title"
    )
    assert json.loads(chunk_path.read_text(encoding="utf-8"))[0]["title"] == (
        "Updated title"
    )
    assert _temporary_files(tmp_path) == []
