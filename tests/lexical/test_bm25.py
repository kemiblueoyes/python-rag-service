import pytest

from rag_service.lexical.bm25 import Bm25Retriever
from rag_service.models.chunk import DocumentChunk


def _chunk(
    *,
    chunk_id: str,
    title: str,
    text: str,
    heading_path: list[str] | None = None,
    content_type: str = "page",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=chunk_id.split(":chunk:")[0],
        source="wordpress",
        source_id=chunk_id,
        title=title,
        url=f"https://example.test/{chunk_id}",
        content_type=content_type,
        text=text,
        heading_path=heading_path or [],
        sequence=0,
    )


def test_search_returns_keyword_relevant_results_first() -> None:
    relevant = _chunk(
        chunk_id="wordpress:page:1:chunk:0",
        title="BM25",
        heading_path=["Keyword Retrieval"],
        text=(
            "BM25 is a keyword ranking algorithm used in "
            "search and retrieval systems."
        ),
    )
    unrelated = _chunk(
        chunk_id="wordpress:page:2:chunk:0",
        title="Chunking",
        text=(
            "Chunking divides documentation into smaller "
            "retrieval units."
        ),
    )

    retriever = Bm25Retriever(
        [unrelated, relevant]
    )

    results = retriever.search(
        "What is BM25?",
        limit=2,
    )

    assert results[0].chunk.chunk_id == relevant.chunk_id
    assert results[0].score > results[1].score


def test_search_respects_limit() -> None:
    chunks = [
        _chunk(
            chunk_id=f"wordpress:page:{index}:chunk:0",
            title="Retrieval",
            text="Search retrieval keyword matching.",
        )
        for index in range(3)
    ]

    retriever = Bm25Retriever(chunks)

    results = retriever.search(
        "retrieval",
        limit=2,
    )

    assert len(results) == 2


def test_search_applies_filters() -> None:
    page = _chunk(
        chunk_id="wordpress:page:1:chunk:0",
        title="Semantic Search",
        text="Semantic search uses embeddings.",
        content_type="page",
    )
    glossary = _chunk(
        chunk_id="wordpress:glossary:2:chunk:0",
        title="Semantic Search",
        text="Semantic search retrieves content by meaning.",
        content_type="glossary",
    )

    retriever = Bm25Retriever(
        [page, glossary]
    )

    results = retriever.search(
        "semantic search",
        limit=5,
        filters={"content_type": "glossary"},
    )

    assert [result.chunk.chunk_id for result in results] == [
        glossary.chunk_id
    ]


def test_search_supports_filter_collections() -> None:
    page = _chunk(
        chunk_id="wordpress:page:1:chunk:0",
        title="Retrieval",
        text="Retrieval systems find relevant content.",
        content_type="page",
    )
    glossary = _chunk(
        chunk_id="wordpress:glossary:2:chunk:0",
        title="Retrieval",
        text="Retrieval finds relevant information.",
        content_type="glossary",
    )

    retriever = Bm25Retriever(
        [page, glossary]
    )

    results = retriever.search(
        "retrieval",
        limit=5,
        filters={
            "content_type": [
                "page",
                "glossary",
            ]
        },
    )

    assert len(results) == 2


@pytest.mark.parametrize(
    "query",
    [
        "",
        " ",
        "   \n\t",
    ],
)
def test_search_rejects_empty_query(
    query: str,
) -> None:
    retriever = Bm25Retriever(
        [
            _chunk(
                chunk_id="wordpress:page:1:chunk:0",
                title="Retrieval",
                text="Retrieval systems.",
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="Query must not be empty",
    ):
        retriever.search(
            query,
            limit=5,
        )


@pytest.mark.parametrize(
    "limit",
    [0, -1],
)
def test_search_rejects_invalid_limit(
    limit: int,
) -> None:
    retriever = Bm25Retriever(
        [
            _chunk(
                chunk_id="wordpress:page:1:chunk:0",
                title="Retrieval",
                text="Retrieval systems.",
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="Search limit must be at least 1",
    ):
        retriever.search(
            "retrieval",
            limit=limit,
        )


def test_constructor_rejects_empty_corpus() -> None:
    with pytest.raises(
        ValueError,
        match="At least one chunk is required",
    ):
        Bm25Retriever([])


def test_search_rejects_unsupported_filter() -> None:
    retriever = Bm25Retriever(
        [
            _chunk(
                chunk_id="wordpress:page:1:chunk:0",
                title="Retrieval",
                text="Retrieval systems.",
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="Unsupported lexical retrieval filter",
    ):
        retriever.search(
            "retrieval",
            limit=5,
            filters={"language": "en-US"},
        )