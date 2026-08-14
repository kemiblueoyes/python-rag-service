from unittest.mock import MagicMock

import pytest

from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval.errors import RetrievalUnavailableError
from rag_service.retrieval.models import RetrievalRequest, RetrievalResult
from rag_service.retrieval.service import RetrievalService
from rag_service.vectorstores.base import SearchResult


def _chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id="wordpress:page:1:chunk:0",
        document_id="wordpress:page:1",
        source="wordpress",
        source_id="1",
        title="Example",
        url="https://example.test/page",
        content_type="page",
        text="Metadata can improve retrieval by narrowing the search space.",
        heading_path=["Metadata"],
        sequence=0,
    )


def test_retrieve_embeds_query_and_searches_vector_store() -> None:
    chunk = _chunk()

    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2]

    vector_store = MagicMock()
    vector_store.search.return_value = [
        SearchResult(chunk=chunk, score=0.91),
    ]

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    request = RetrievalRequest(
        query="How does metadata improve retrieval?",
        limit=3,
        filters={"content_type": "page"},
    )

    results = service.retrieve(request)

    embedding_provider.embed_query.assert_called_once_with(
        "How does metadata improve retrieval?"
    )

    vector_store.search.assert_called_once_with(
        query_vector=[0.1, 0.2],
        limit=3,
        filters={"content_type": "page"},
    )

    assert results == [
        RetrievalResult(
            chunk=chunk,
            score=0.91,
        )
    ]


def test_retrieve_passes_none_when_no_filters_are_provided() -> None:
    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2]

    vector_store = MagicMock()
    vector_store.search.return_value = []

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    service.retrieve(
        RetrievalRequest(
            query="What is RAG?",
        )
    )

    vector_store.search.assert_called_once_with(
        query_vector=[0.1, 0.2],
        limit=5,
        filters=None,
    )

@pytest.mark.parametrize("query", ["", " ", "   \n\t"])
def test_retrieve_rejects_empty_query(query: str) -> None:
    embedding_provider = MagicMock()
    vector_store = MagicMock()

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(ValueError, match="Query must not be empty"):
        service.retrieve(RetrievalRequest(query=query))

    embedding_provider.embed_query.assert_not_called()
    vector_store.search.assert_not_called()


@pytest.mark.parametrize("limit", [0, -1])
def test_retrieve_rejects_invalid_limit(limit: int) -> None:
    embedding_provider = MagicMock()
    vector_store = MagicMock()

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(ValueError, match="Retrieval limit must be at least 1"):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?",
                limit=limit,
            )
        )

    embedding_provider.embed_query.assert_not_called()
    vector_store.search.assert_not_called()


def test_retrieve_strips_query_whitespace_before_embedding() -> None:
    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2]

    vector_store = MagicMock()
    vector_store.search.return_value = []

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    service.retrieve(
        RetrievalRequest(
            query="  What is RAG?  ",
        )
    )

    embedding_provider.embed_query.assert_called_once_with("What is RAG?")

def test_retrieve_rejects_unsupported_filter() -> None:
    embedding_provider = MagicMock()
    vector_store = MagicMock()

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(
        ValueError,
        match="Unsupported retrieval filter",
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?",
                filters={"language": "en-US"},
            )
        )

    embedding_provider.embed_query.assert_not_called()
    vector_store.search.assert_not_called()


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("", "must not be empty"),
        ([], "must not be empty"),
        (123, "must be a string or collection of strings"),
    ],
)
def test_retrieve_rejects_invalid_filter_value(
    value: object,
    message: str,
) -> None:
    embedding_provider = MagicMock()
    vector_store = MagicMock()

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(ValueError, match=message):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?",
                filters={"content_type": value},
            )
        )


def test_retrieve_rejects_invalid_filter_collection_items() -> None:
    embedding_provider = MagicMock()
    vector_store = MagicMock()

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(
        ValueError,
        match="must contain only non-empty strings",
    ):
        service.retrieve(
            RetrievalRequest(
                query="What is RAG?",
                filters={"content_type": ["page", ""]},
            )
        )

def test_retrieve_removes_duplicate_chunks() -> None:
    chunk = _chunk()

    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2]

    vector_store = MagicMock()
    vector_store.search.return_value = [
        SearchResult(chunk=chunk, score=0.91),
        SearchResult(chunk=chunk, score=0.85),
    ]

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    results = service.retrieve(
        RetrievalRequest(
            query="How does metadata improve retrieval?",
        )
    )

    assert results == [
        RetrievalResult(
            chunk=chunk,
            score=0.91,
        )
    ]

def test_retrieve_preserves_similarity_ranking() -> None:
    # Qdrant ranks by cosine similarity; RetrievalService preserves that order.
    first = _chunk()
    second = first.model_copy(
        update={
            "chunk_id": "wordpress:page:2:chunk:0",
            "document_id": "wordpress:page:2",
            "source_id": "2",
            "title": "Second Example",
        }
    )

    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2]

    vector_store = MagicMock()
    vector_store.search.return_value = [
        SearchResult(chunk=first, score=0.93),
        SearchResult(chunk=second, score=0.81),
    ]

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    results = service.retrieve(
        RetrievalRequest(
            query="How does metadata improve retrieval?",
            limit=2,
        )
    )

    assert [result.chunk.chunk_id for result in results] == [
        first.chunk_id,
        second.chunk_id,
    ]

    assert [result.score for result in results] == [
        0.93,
        0.81,
    ]

def test_retrieve_removes_results_below_minimum_score() -> None:
    relevant = _chunk()
    weak = relevant.model_copy(
        update={
            "chunk_id": "wordpress:page:2:chunk:0",
            "document_id": "wordpress:page:2",
            "source_id": "2",
        }
    )

    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2]

    vector_store = MagicMock()
    vector_store.search.return_value = [
        SearchResult(chunk=relevant, score=0.67),
        SearchResult(chunk=weak, score=0.49),
    ]

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        min_score=0.50,
    )

    results = service.retrieve(
        RetrievalRequest(query="What is RAG?")
    )

    assert results == [
        RetrievalResult(
            chunk=relevant,
            score=0.67,
        )
    ]


def test_retrieve_returns_empty_when_all_results_are_too_weak() -> None:
    chunk = _chunk()

    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2]

    vector_store = MagicMock()
    vector_store.search.return_value = [
        SearchResult(chunk=chunk, score=0.35),
    ]

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        min_score=0.50,
    )

    results = service.retrieve(
        RetrievalRequest(
            query="How do I configure Kubernetes autoscaling?"
        )
    )

    assert results == []


def test_retrieval_minimum_score_is_configurable() -> None:
    chunk = _chunk()

    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2]

    vector_store = MagicMock()
    vector_store.search.return_value = [
        SearchResult(chunk=chunk, score=0.59),
    ]

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        min_score=0.60,
    )

    results = service.retrieve(
        RetrievalRequest(query="What is RAG?")
    )

    assert results == []

def test_retrieve_wraps_embedding_provider_failure() -> None:
    embedding_provider = MagicMock()
    embedding_provider.embed_query.side_effect = RuntimeError(
        "Voyage unavailable"
    )

    vector_store = MagicMock()

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(
        RetrievalUnavailableError,
        match="Retrieval could not be completed",
    ):
        service.retrieve(
            RetrievalRequest(query="What is RAG?")
        )

    vector_store.search.assert_not_called()


def test_retrieve_wraps_vector_store_failure() -> None:
    embedding_provider = MagicMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2]

    vector_store = MagicMock()
    vector_store.search.side_effect = RuntimeError(
        "Qdrant unavailable"
    )

    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(
        RetrievalUnavailableError,
        match="Retrieval could not be completed",
    ):
        service.retrieve(
            RetrievalRequest(query="What is RAG?")
        )