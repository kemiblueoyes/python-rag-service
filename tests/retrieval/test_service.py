from unittest.mock import MagicMock

import pytest

from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval.errors import RetrievalUnavailableError
from rag_service.retrieval.models import RetrievalRequest, RetrievalResult
from rag_service.retrieval.service import RetrievalService
from rag_service.vectorstores.base import SearchResult


def _chunk(
    *,
    chunk_id: str = "wordpress:page:1:chunk:0",
    title: str = "Example",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=chunk_id.split(":chunk:")[0],
        source="wordpress",
        source_id=chunk_id,
        title=title,
        url=f"https://example.test/{chunk_id}",
        content_type="page",
        text="Metadata can improve retrieval.",
        heading_path=["Metadata"],
        sequence=0,
    )


def _service(
    *,
    support_cutoff: float = 0.70,
) -> tuple[
    RetrievalService,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [
        0.1,
        0.2,
    ]

    vector_store = MagicMock()
    vector_store.search.return_value = []

    lexical_retriever = MagicMock()
    lexical_retriever.search.return_value = []

    reranker = MagicMock()
    reranker.rerank.return_value = []

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        lexical_retriever=lexical_retriever,
        reranker=reranker,
        support_cutoff=support_cutoff,
    )

    return (
        service,
        embedding_provider,
        vector_store,
        lexical_retriever,
        reranker,
    )


def test_retrieve_runs_semantic_and_lexical_retrieval() -> None:
    (
        service,
        embedding_provider,
        vector_store,
        lexical_retriever,
        reranker,
    ) = _service()

    chunk = _chunk()

    vector_store.search.return_value = [
        SearchResult(
            chunk=chunk,
            score=0.61,
        )
    ]

    lexical_retriever.search.return_value = [
        SearchResult(
            chunk=chunk,
            score=4.2,
        )
    ]

    reranker.rerank.return_value = [
        SearchResult(
            chunk=chunk,
            score=0.91,
        )
    ]

    results = service.retrieve(
        RetrievalRequest(
            query="How does metadata improve retrieval?",
            limit=5,
            filters={"content_type": "page"},
        )
    )

    embedding_provider.embed_query.assert_called_once_with(
        "How does metadata improve retrieval?"
    )

    vector_store.search.assert_called_once_with(
        query_vector=[0.1, 0.2],
        limit=20,
        filters={"content_type": "page"},
    )

    lexical_retriever.search.assert_called_once_with(
        "How does metadata improve retrieval?",
        limit=20,
        filters={"content_type": "page"},
    )

    reranker.rerank.assert_called_once()

    assert results == [
        RetrievalResult(
            chunk=chunk,
            score=0.91,
        )
    ]


def test_retrieve_passes_fused_candidates_to_reranker() -> None:
    (
        service,
        _,
        vector_store,
        lexical_retriever,
        reranker,
    ) = _service()

    shared = _chunk(
        chunk_id="wordpress:page:1:chunk:0",
    )
    semantic_only = _chunk(
        chunk_id="wordpress:page:2:chunk:0",
    )
    lexical_only = _chunk(
        chunk_id="wordpress:page:3:chunk:0",
    )

    vector_store.search.return_value = [
        SearchResult(
            chunk=shared,
            score=0.80,
        ),
        SearchResult(
            chunk=semantic_only,
            score=0.70,
        ),
    ]

    lexical_retriever.search.return_value = [
        SearchResult(
            chunk=shared,
            score=5.0,
        ),
        SearchResult(
            chunk=lexical_only,
            score=4.0,
        ),
    ]

    reranker.rerank.return_value = [
        SearchResult(
            chunk=shared,
            score=0.90,
        )
    ]

    service.retrieve(
        RetrievalRequest(
            query="retrieval",
            limit=5,
        )
    )

    reranker.rerank.assert_called_once()

    _, candidates = reranker.rerank.call_args.args

    assert [
        result.chunk.chunk_id
        for result in candidates
    ] == [
        shared.chunk_id,
        semantic_only.chunk_id,
        lexical_only.chunk_id,
    ]


def test_retrieve_uses_configured_candidate_depths() -> None:
    (
        _,
        embedding_provider,
        vector_store,
        lexical_retriever,
        reranker,
    ) = _service()

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        lexical_retriever=lexical_retriever,
        reranker=reranker,
        vector_candidate_depth=12,
        lexical_candidate_depth=15,
        fused_candidate_depth=10,
    )

    service.retrieve(
        RetrievalRequest(
            query="What is RAG?",
        )
    )

    vector_store.search.assert_called_once_with(
        query_vector=[0.1, 0.2],
        limit=12,
        filters=None,
    )

    lexical_retriever.search.assert_called_once_with(
        "What is RAG?",
        limit=15,
        filters=None,
    )


def test_retrieve_returns_empty_when_no_candidates_exist() -> None:
    (
        service,
        _,
        _,
        _,
        reranker,
    ) = _service()

    results = service.retrieve(
        RetrievalRequest(
            query="What is RAG?"
        )
    )

    assert results == []
    reranker.rerank.assert_not_called()


def test_retrieve_rejects_query_below_support_cutoff() -> None:
    (
        service,
        _,
        vector_store,
        _,
        reranker,
    ) = _service(
        support_cutoff=0.70,
    )

    chunk = _chunk()

    vector_store.search.return_value = [
        SearchResult(
            chunk=chunk,
            score=0.65,
        )
    ]

    reranker.rerank.return_value = [
        SearchResult(
            chunk=chunk,
            score=0.69,
        )
    ]

    results = service.retrieve(
        RetrievalRequest(
            query="Unsupported question"
        )
    )

    assert results == []


def test_retrieve_accepts_query_at_support_cutoff() -> None:
    (
        service,
        _,
        vector_store,
        _,
        reranker,
    ) = _service(
        support_cutoff=0.70,
    )

    chunk = _chunk()

    vector_store.search.return_value = [
        SearchResult(
            chunk=chunk,
            score=0.60,
        )
    ]

    reranker.rerank.return_value = [
        SearchResult(
            chunk=chunk,
            score=0.70,
        )
    ]

    results = service.retrieve(
        RetrievalRequest(
            query="Supported question"
        )
    )

    assert results == [
        RetrievalResult(
            chunk=chunk,
            score=0.70,
        )
    ]


def test_support_gate_is_query_level_not_result_level() -> None:
    (
        service,
        _,
        vector_store,
        _,
        reranker,
    ) = _service()

    first = _chunk(
        chunk_id="wordpress:page:1:chunk:0",
    )
    second = _chunk(
        chunk_id="wordpress:page:2:chunk:0",
    )

    vector_store.search.return_value = [
        SearchResult(
            chunk=first,
            score=0.60,
        ),
        SearchResult(
            chunk=second,
            score=0.59,
        ),
    ]

    reranker.rerank.return_value = [
        SearchResult(
            chunk=first,
            score=0.90,
        ),
        SearchResult(
            chunk=second,
            score=0.55,
        ),
    ]

    results = service.retrieve(
        RetrievalRequest(
            query="Supported question",
            limit=2,
        )
    )

    assert [
        result.score
        for result in results
    ] == [
        0.90,
        0.55,
    ]


def test_retrieve_returns_rerank_scores() -> None:
    (
        service,
        _,
        vector_store,
        _,
        reranker,
    ) = _service()

    chunk = _chunk()

    vector_store.search.return_value = [
        SearchResult(
            chunk=chunk,
            score=0.61,
        )
    ]

    reranker.rerank.return_value = [
        SearchResult(
            chunk=chunk,
            score=0.93,
        )
    ]

    results = service.retrieve(
        RetrievalRequest(
            query="What is RAG?"
        )
    )

    assert results[0].score == 0.93


def test_retrieve_respects_requested_limit() -> None:
    (
        service,
        _,
        vector_store,
        _,
        reranker,
    ) = _service()

    first = _chunk(
        chunk_id="wordpress:page:1:chunk:0",
    )
    second = _chunk(
        chunk_id="wordpress:page:2:chunk:0",
    )

    vector_store.search.return_value = [
        SearchResult(
            chunk=first,
            score=0.60,
        ),
        SearchResult(
            chunk=second,
            score=0.59,
        ),
    ]

    reranker.rerank.return_value = [
        SearchResult(
            chunk=first,
            score=0.90,
        )
    ]

    service.retrieve(
        RetrievalRequest(
            query="retrieval",
            limit=1,
        )
    )

    reranker.rerank.assert_called_once()

    assert (
        reranker.rerank.call_args.kwargs["limit"]
        == 1
    )


def test_retrieve_strips_query_whitespace() -> None:
    (
        service,
        embedding_provider,
        _,
        lexical_retriever,
        _,
    ) = _service()

    service.retrieve(
        RetrievalRequest(
            query="  What is RAG?  ",
        )
    )

    embedding_provider.embed_query.assert_called_once_with(
        "What is RAG?"
    )

    lexical_retriever.search.assert_called_once_with(
        "What is RAG?",
        limit=20,
        filters=None,
    )


@pytest.mark.parametrize(
    "query",
    ["", " ", "   \n\t"],
)
def test_retrieve_rejects_empty_query(
    query: str,
) -> None:
    (
        service,
        embedding_provider,
        vector_store,
        lexical_retriever,
        reranker,
    ) = _service()

    with pytest.raises(
        ValueError,
        match="Query must not be empty",
    ):
        service.retrieve(
            RetrievalRequest(
                query=query
            )
        )

    embedding_provider.embed_query.assert_not_called()
    vector_store.search.assert_not_called()
    lexical_retriever.search.assert_not_called()
    reranker.rerank.assert_not_called()


@pytest.mark.parametrize(
    "limit",
    [0, -1],
)
def test_retrieve_rejects_invalid_limit(
    limit: int,
) -> None:
    service, *_ = _service()

    with pytest.raises(
        ValueError,
        match="Retrieval limit must be at least 1",
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?",
                limit=limit,
            )
        )


def test_retrieve_rejects_unsupported_filter() -> None:
    service, *_ = _service()

    with pytest.raises(
        ValueError,
        match="Unsupported retrieval filter",
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?",
                filters={
                    "language": "en-US"
                },
            )
        )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("", "must not be empty"),
        ([], "must not be empty"),
        (
            123,
            "must be a string or collection of strings",
        ),
    ],
)
def test_retrieve_rejects_invalid_filter_value(
    value: object,
    message: str,
) -> None:
    service, *_ = _service()

    with pytest.raises(
        ValueError,
        match=message,
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?",
                filters={
                    "content_type": value
                },
            )
        )


def test_retrieve_rejects_invalid_filter_collection_items() -> None:
    service, *_ = _service()

    with pytest.raises(
        ValueError,
        match="must contain only non-empty strings",
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?",
                filters={
                    "content_type": [
                        "page",
                        "",
                    ]
                },
            )
        )


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "vector_candidate_depth",
            0,
            "Vector candidate depth",
        ),
        (
            "lexical_candidate_depth",
            0,
            "Lexical candidate depth",
        ),
        (
            "fused_candidate_depth",
            0,
            "Fused candidate depth",
        ),
        (
            "rrf_k",
            0,
            "RRF constant",
        ),
        (
            "support_cutoff",
            -0.1,
            "Support cutoff",
        ),
        (
            "support_cutoff",
            1.1,
            "Support cutoff",
        ),
    ],
)
def test_constructor_rejects_invalid_configuration(
    field: str,
    value: int | float,
    message: str,
) -> None:
    (
        _,
        embedding_provider,
        vector_store,
        lexical_retriever,
        reranker,
    ) = _service()

    kwargs: dict[str, object] = {
        "embedding_provider": embedding_provider,
        "vector_store": vector_store,
        "lexical_retriever": lexical_retriever,
        "reranker": reranker,
        field: value,
    }

    with pytest.raises(
        ValueError,
        match=message,
    ):
        RetrievalService(**kwargs)  # type: ignore[arg-type]


def test_retrieve_wraps_embedding_provider_failure() -> None:
    (
        service,
        embedding_provider,
        vector_store,
        lexical_retriever,
        _,
    ) = _service()

    embedding_provider.embed_query.side_effect = (
        RuntimeError("Voyage unavailable")
    )

    with pytest.raises(
        RetrievalUnavailableError,
        match="Retrieval could not be completed",
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?"
            )
        )

    vector_store.search.assert_not_called()
    lexical_retriever.search.assert_not_called()


def test_retrieve_wraps_vector_store_failure() -> None:
    (
        service,
        _,
        vector_store,
        lexical_retriever,
        _,
    ) = _service()

    vector_store.search.side_effect = (
        RuntimeError("Qdrant unavailable")
    )

    with pytest.raises(
        RetrievalUnavailableError,
        match="Retrieval could not be completed",
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?"
            )
        )

    lexical_retriever.search.assert_not_called()


def test_retrieve_wraps_lexical_retriever_failure() -> None:
    (
        service,
        _,
        vector_store,
        lexical_retriever,
        reranker,
    ) = _service()

    vector_store.search.return_value = []

    lexical_retriever.search.side_effect = (
        RuntimeError("BM25 unavailable")
    )

    with pytest.raises(
        RetrievalUnavailableError,
        match="Retrieval could not be completed",
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?"
            )
        )

    reranker.rerank.assert_not_called()


def test_retrieve_wraps_reranker_failure() -> None:
    (
        service,
        _,
        vector_store,
        _,
        reranker,
    ) = _service()

    chunk = _chunk()

    vector_store.search.return_value = [
        SearchResult(
            chunk=chunk,
            score=0.60,
        )
    ]

    reranker.rerank.side_effect = (
        RuntimeError("Voyage reranking unavailable")
    )

    with pytest.raises(
        RetrievalUnavailableError,
        match="Retrieval could not be completed",
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?"
            )
        )