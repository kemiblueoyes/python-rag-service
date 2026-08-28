from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from rag_service.api.app import app
from rag_service.api.dependencies import get_retrieval_service
from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval import (
    RetrievalResult,
    RetrievalService,
    RetrievalUnavailableError,
)


@pytest.mark.parametrize("query", ["", " ", "   \n\t"])
def test_search_rejects_empty_query(query: str) -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/search",
        json={"query": query},
    )

    assert response.status_code == 422


def test_search_rejects_limit_below_one() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/search",
        json={
            "query": "What is RAG?",
            "limit": 0,
        },
    )

    assert response.status_code == 422


def test_search_rejects_unsupported_filter() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/search",
        json={
            "query": "What is RAG?",
            "filters": {
                "site_id": "the-doc-landscape",
            },
        },
    )

    assert response.status_code == 422


def test_search_returns_empty_results_when_nothing_is_relevant() -> None:
    service = MagicMock(spec=RetrievalService)
    service.retrieve.return_value = []

    app.dependency_overrides[get_retrieval_service] = lambda: service

    try:
        client = TestClient(app)

        response = client.post(
            "/v1/search",
            json={"query": "Something unrelated"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "query": "Something unrelated",
            "results": [],
        }

    finally:
        app.dependency_overrides.clear()

def _chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id="wordpress:page:1:chunk:0",
        document_id="wordpress:page:1",
        source="wordpress",
        source_id="1",
        title="Metadata Strategy",
        url="https://example.test/metadata",
        content_type="page",
        text="Metadata can narrow the documents considered during retrieval.",
        heading_path=["Metadata filtering"],
        anchor="metadata-filtering",
        sequence=0,
    )


def test_search_returns_ranked_results() -> None:
    service = MagicMock(spec=RetrievalService)
    service.retrieve.return_value = [
        RetrievalResult(
            chunk=_chunk(),
            score=0.91,
        )
    ]

    app.dependency_overrides[get_retrieval_service] = lambda: service

    try:
        client = TestClient(app)

        response = client.post(
            "/v1/search",
            json={
                "query": "How does metadata improve retrieval?",
                "filters": {
                    "content_type": "page",
                },
                "limit": 3,
            },
        )

        assert response.status_code == 200

        assert response.json() == {
            "query": "How does metadata improve retrieval?",
            "results": [
                {
                    "chunk_id": "wordpress:page:1:chunk:0",
                    "document_id": "wordpress:page:1",
                    "title": "Metadata Strategy",
                    "heading_path": ["Metadata filtering"],
                    "anchor": "metadata-filtering",
                    "excerpt": (
                        "Metadata can narrow the documents "
                        "considered during retrieval."
                    ),
                    "url": "https://example.test/metadata",
                    "score": 0.91,
                }
            ],
        }

        service.retrieve.assert_called_once()

        retrieval_request = service.retrieve.call_args.args[0]

        assert retrieval_request.query == (
            "How does metadata improve retrieval?"
        )
        assert retrieval_request.limit == 3
        assert retrieval_request.filters == {
            "content_type": "page",
        }

    finally:
        app.dependency_overrides.clear()

def test_search_validation_does_not_build_retrieval_service() -> None:
    get_retrieval_service.cache_clear()

    try:
        with patch(
            "rag_service.api.dependencies.create_retrieval_service",
        ) as create_service:
            client = TestClient(app)

            response = client.post(
                "/v1/search",
                json={"query": ""},
            )

        assert response.status_code == 422
        create_service.assert_not_called()
    finally:
        get_retrieval_service.cache_clear()


def test_search_returns_standard_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/search",
        json={
            "query": "What is RAG?",
            "filters": {
                "site_id": "the-doc-landscape",
            },
        },
    )

    assert response.status_code == 422

    body = response.json()

    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed."
    assert body["error"]["details"][0]["field"] == "filters.site_id"
    assert body["error"]["details"][0]["message"]

def test_search_openapi_documents_validation_error() -> None:
    schema = app.openapi()

    search_operation = schema["paths"]["/v1/search"]["post"]

    validation_response = search_operation["responses"]["422"]

    assert validation_response["description"] == (
        "Request validation failed."
    )

    error_schema = validation_response["content"]["application/json"]["schema"]

    assert error_schema == {
        "$ref": "#/components/schemas/ErrorResponse"
    }

def test_search_returns_503_when_retrieval_is_unavailable() -> None:
    service = MagicMock(spec=RetrievalService)
    service.retrieve.side_effect = RetrievalUnavailableError(
        "Retrieval could not be completed."
    )

    app.dependency_overrides[get_retrieval_service] = lambda: service

    try:
        client = TestClient(app)

        response = client.post(
            "/v1/search",
            json={"query": "What is RAG?"},
        )

        assert response.status_code == 503
        assert response.json() == {
            "error": {
                "code": "retrieval_unavailable",
                "message": "Search is temporarily unavailable.",
                "details": [],
            }
        }

    finally:
        app.dependency_overrides.clear()

def test_search_openapi_documents_service_unavailable_error() -> None:
    schema = app.openapi()

    search_operation = schema["paths"]["/v1/search"]["post"]

    unavailable_response = search_operation["responses"]["503"]

    assert unavailable_response["description"] == (
        "Search is temporarily unavailable."
    )

    error_schema = unavailable_response["content"]["application/json"]["schema"]

    assert error_schema == {
        "$ref": "#/components/schemas/ErrorResponse"
    }