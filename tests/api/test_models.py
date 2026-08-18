import pytest
from pydantic import ValidationError

from rag_service.api.models import AnswerRequest, SearchRequest


def test_search_request_defaults() -> None:
    request = SearchRequest(
        query="What is RAG?",
    )

    assert request.query == "What is RAG?"
    assert request.limit == 5
    assert request.filters is None


def test_search_request_strips_query_whitespace() -> None:
    request = SearchRequest(
        query="  What is RAG?  ",
    )

    assert request.query == "What is RAG?"


@pytest.mark.parametrize("query", ["", " ", "   \n\t"])
def test_search_request_rejects_empty_query(query: str) -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query=query)


def test_search_request_rejects_limit_below_one() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(
            query="What is RAG?",
            limit=0,
        )


def test_search_request_accepts_supported_filters() -> None:
    request = SearchRequest(
        query="What is RAG?",
        filters={
            "source": "wordpress",
            "content_type": ["page", "post"],
        },
    )

    assert request.filters is not None
    assert request.filters.source == "wordpress"
    assert request.filters.content_type == ["page", "post"]


def test_search_request_rejects_unsupported_filter() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(
            query="What is RAG?",
            filters={"site_id": "the-doc-landscape"},
        )

def test_answer_request_defaults() -> None:
    request = AnswerRequest(
        query="Why does retrieval fail?",
    )

    assert request.query == "Why does retrieval fail?"
    assert request.filters is None


def test_answer_request_strips_query_whitespace() -> None:
    request = AnswerRequest(
        query="  Why does retrieval fail?  ",
    )

    assert request.query == "Why does retrieval fail?"


@pytest.mark.parametrize("query", ["", " ", "   \n\t"])
def test_answer_request_rejects_empty_query(query: str) -> None:
    with pytest.raises(ValidationError):
        AnswerRequest(query=query)


def test_answer_request_accepts_supported_filters() -> None:
    request = AnswerRequest(
        query="Why does retrieval fail?",
        filters={
            "source": "wordpress",
            "content_type": ["page", "post"],
        },
    )

    assert request.filters is not None
    assert request.filters.source == "wordpress"
    assert request.filters.content_type == ["page", "post"]


def test_answer_request_rejects_unsupported_filter() -> None:
    with pytest.raises(ValidationError):
        AnswerRequest(
            query="Why does retrieval fail?",
            filters={"site_id": "the-doc-landscape"},
        )


def test_answer_request_rejects_retrieval_limit() -> None:
    with pytest.raises(ValidationError):
        AnswerRequest(
            query="Why does retrieval fail?",
            limit=5,
        )