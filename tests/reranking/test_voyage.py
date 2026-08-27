from dataclasses import dataclass

import pytest

from rag_service.models.chunk import DocumentChunk
from rag_service.reranking.voyage import VoyageReranker
from rag_service.vectorstores.base import SearchResult


@dataclass
class _FakeRerankingResult:
    index: int
    relevance_score: float


@dataclass
class _FakeRerankingResponse:
    results: list[_FakeRerankingResult]


class _FakeVoyageClient:
    def __init__(
        self,
        results: list[_FakeRerankingResult],
    ) -> None:
        self.results = results

    def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        model: str,
        top_k: int | None = None,
        truncation: bool = True,
    ) -> _FakeRerankingResponse:
        return _FakeRerankingResponse(
            results=self.results
        )


def _result(
    chunk_id: str,
    *,
    title: str = "Example",
    heading_path: list[str] | None = None,
    text: str = "Example retrieval content.",
    score: float = 0.5,
) -> SearchResult:
    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id=chunk_id.split(":chunk:")[0],
        source="wordpress",
        source_id=chunk_id,
        title=title,
        url=f"https://example.test/{chunk_id}",
        content_type="page",
        text=text,
        heading_path=heading_path or [],
        sequence=0,
    )

    return SearchResult(
        chunk=chunk,
        score=score,
    )


def test_rerank_returns_voyage_order_and_scores() -> None:
    first = _result(
        "wordpress:page:1:chunk:0",
        score=0.90,
    )
    second = _result(
        "wordpress:page:2:chunk:0",
        score=0.80,
    )

    client = _FakeVoyageClient(
        [
            _FakeRerankingResult(
                index=1,
                relevance_score=0.95,
            ),
            _FakeRerankingResult(
                index=0,
                relevance_score=0.75,
            ),
        ]
    )

    reranker = VoyageReranker(
        client=client,
    )

    results = reranker.rerank(
        "What is retrieval?",
        [first, second],
        limit=2,
    )

    assert [
        result.chunk.chunk_id
        for result in results
    ] == [
        second.chunk.chunk_id,
        first.chunk.chunk_id,
    ]

    assert [
        result.score
        for result in results
    ] == [
        0.95,
        0.75,
    ]


def test_rerank_returns_empty_for_empty_results() -> None:
    client = _FakeVoyageClient([])

    reranker = VoyageReranker(
        client=client,
    )

    assert reranker.rerank(
        "What is retrieval?",
        [],
        limit=5,
    ) == []


@pytest.mark.parametrize(
    "query",
    ["", " ", "   \n\t"],
)
def test_rerank_rejects_empty_query(
    query: str,
) -> None:
    client = _FakeVoyageClient([])

    reranker = VoyageReranker(
        client=client,
    )

    with pytest.raises(
        ValueError,
        match="Query must not be empty",
    ):
        reranker.rerank(
            query,
            [],
            limit=5,
        )


@pytest.mark.parametrize(
    "limit",
    [0, -1],
)
def test_rerank_rejects_invalid_limit(
    limit: int,
) -> None:
    client = _FakeVoyageClient([])

    reranker = VoyageReranker(
        client=client,
    )

    with pytest.raises(
        ValueError,
        match="Rerank limit must be at least 1",
    ):
        reranker.rerank(
            "retrieval",
            [],
            limit=limit,
        )


def test_rerank_rejects_invalid_candidate_index() -> None:
    candidate = _result(
        "wordpress:page:1:chunk:0"
    )

    client = _FakeVoyageClient(
        [
            _FakeRerankingResult(
                index=10,
                relevance_score=0.90,
            )
        ]
    )

    reranker = VoyageReranker(
        client=client,
    )

    with pytest.raises(
        RuntimeError,
        match="invalid candidate index",
    ):
        reranker.rerank(
            "retrieval",
            [candidate],
            limit=1,
        )


def test_rerank_document_includes_context() -> None:
    candidate = _result(
        "wordpress:page:1:chunk:0",
        title="BM25",
        heading_path=[
            "Retrieval",
            "Keyword Search",
        ],
        text="BM25 ranks documents using lexical signals.",
    )

    document = VoyageReranker._document_for_reranking(
        candidate
    )

    assert document == (
        "Title: BM25\n"
        "Heading: Retrieval > Keyword Search\n"
        "Content:\n"
        "BM25 ranks documents using lexical signals."
    )