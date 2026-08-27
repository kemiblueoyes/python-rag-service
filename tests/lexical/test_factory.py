import json
from pathlib import Path

import pytest

from rag_service.config import Settings
from rag_service.lexical import (
    Bm25Retriever,
    create_lexical_retriever,
    load_lexical_corpus,
)
from rag_service.models.chunk import DocumentChunk


def _chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id="wordpress:page:1:chunk:0",
        document_id="wordpress:page:1",
        source="wordpress",
        source_id="1",
        title="BM25",
        url="https://example.test/bm25",
        content_type="page",
        text="BM25 is a keyword-based retrieval algorithm.",
        heading_path=["Keyword Retrieval"],
        sequence=0,
    )


def _write_corpus(
    path: Path,
    chunks: list[DocumentChunk],
) -> None:
    path.write_text(
        json.dumps(
            [
                chunk.model_dump(mode="json")
                for chunk in chunks
            ]
        ),
        encoding="utf-8",
    )


def test_load_lexical_corpus_loads_chunks(
    tmp_path: Path,
) -> None:
    corpus_path = tmp_path / "chunks.json"
    chunk = _chunk()

    _write_corpus(
        corpus_path,
        [chunk],
    )

    chunks = load_lexical_corpus(
        corpus_path
    )

    assert chunks == [chunk]


def test_load_lexical_corpus_rejects_missing_file(
    tmp_path: Path,
) -> None:
    corpus_path = tmp_path / "missing.json"

    with pytest.raises(
        FileNotFoundError,
        match="Lexical corpus does not exist",
    ):
        load_lexical_corpus(
            corpus_path
        )


def test_load_lexical_corpus_rejects_non_list_payload(
    tmp_path: Path,
) -> None:
    corpus_path = tmp_path / "chunks.json"

    corpus_path.write_text(
        json.dumps(
            {"chunk": "not a list"}
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Expected a chunk list",
    ):
        load_lexical_corpus(
            corpus_path
        )


def test_create_lexical_retriever_builds_bm25(
    tmp_path: Path,
) -> None:
    corpus_path = tmp_path / "chunks.json"

    _write_corpus(
        corpus_path,
        [_chunk()],
    )

    settings = Settings(
        lexical_corpus_path=corpus_path,
    )

    retriever = create_lexical_retriever(
        settings
    )

    assert isinstance(
        retriever,
        Bm25Retriever,
    )


def test_created_retriever_can_search_corpus(
    tmp_path: Path,
) -> None:
    corpus_path = tmp_path / "chunks.json"
    chunk = _chunk()

    _write_corpus(
        corpus_path,
        [chunk],
    )

    settings = Settings(
        lexical_corpus_path=corpus_path,
    )

    retriever = create_lexical_retriever(
        settings
    )

    results = retriever.search(
        "BM25 retrieval",
        limit=1,
    )

    assert len(results) == 1
    assert results[0].chunk.chunk_id == chunk.chunk_id