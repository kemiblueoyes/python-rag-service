from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from rag_service.api.app import app
from rag_service.api.dependencies import (
    get_answer_generator,
    get_retrieval_service,
)
from rag_service.generation import AnswerGenerator, GeneratedAnswer
from rag_service.generation.errors import (
    CitationValidationError,
    ContextBudgetError,
    LanguageModelProviderError,
)
from rag_service.generation.models import ContextSource
from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval import (
    RetrievalResult,
    RetrievalService,
    RetrievalUnavailableError,
)


def _chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id="wordpress:page:1:chunk:0",
        document_id="wordpress:page:1",
        source="wordpress",
        source_id="1",
        title="Retrieval Failures",
        url="https://example.test/retrieval-failures",
        content_type="page",
        text=(
            "Inconsistent terminology can make relevant content "
            "harder to retrieve."
        ),
        heading_path=["Vocabulary mismatch"],
        anchor="vocabulary-mismatch",
        sequence=0,
    )


def test_answer_returns_grounded_response() -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    answer_generator = MagicMock(spec=AnswerGenerator)

    retrieval_results = [
        RetrievalResult(
            chunk=_chunk(),
            score=0.91,
        )
    ]

    retrieval_service.retrieve.return_value = retrieval_results

    answer_generator.generate.return_value = GeneratedAnswer(
        answer=(
            "Inconsistent terminology can cause retrieval failures "
            "because the query and documentation may use different "
            "language for the same concept. [S1]"
        ),
        sources=(
            ContextSource(
                citation_id="S1",
                chunk=_chunk(),
                score=0.91,
            ),
        ),
        sufficient_evidence=True,
    )

    app.dependency_overrides[get_retrieval_service] = (
        lambda: retrieval_service
    )
    app.dependency_overrides[get_answer_generator] = (
        lambda: answer_generator
    )

    try:
        client = TestClient(app)

        response = client.post(
            "/v1/answer",
            json={
                "query": (
                    "Why does inconsistent terminology "
                    "cause retrieval failures?"
                ),
                "filters": {
                    "source": "wordpress",
                },
            },
        )

        assert response.status_code == 200

        assert response.json() == {
            "query": (
                "Why does inconsistent terminology "
                "cause retrieval failures?"
            ),
            "answer": (
                "Inconsistent terminology can cause retrieval failures "
                "because the query and documentation may use different "
                "language for the same concept. [S1]"
            ),
            "sources": [
                {
                    "citation_id": "S1",
                    "chunk_id": "wordpress:page:1:chunk:0",
                    "document_id": "wordpress:page:1",
                    "title": "Retrieval Failures",
                    "heading_path": ["Vocabulary mismatch"],
                    "anchor": "vocabulary-mismatch",
                    "excerpt": (
                        "Inconsistent terminology can make relevant "
                        "content harder to retrieve."
                    ),
                    "url": (
                        "https://example.test/retrieval-failures"
                    ),
                }
            ],
            "sufficient_evidence": True,
        }

        retrieval_service.retrieve.assert_called_once()

        retrieval_request = (
            retrieval_service.retrieve.call_args.args[0]
        )

        assert retrieval_request.query == (
            "Why does inconsistent terminology "
            "cause retrieval failures?"
        )
        assert retrieval_request.limit == 5
        assert retrieval_request.filters == {
            "source": "wordpress",
        }

        answer_generator.generate.assert_called_once_with(
            question=(
                "Why does inconsistent terminology "
                "cause retrieval failures?"
            ),
            results=retrieval_results,
        )

    finally:
        app.dependency_overrides.clear()


def test_answer_returns_insufficient_evidence_response() -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    answer_generator = MagicMock(spec=AnswerGenerator)

    retrieval_service.retrieve.return_value = []

    answer_generator.generate.return_value = GeneratedAnswer(
        answer=(
            "The available documentation does not provide enough "
            "information to answer this question."
        ),
        sources=(),
        sufficient_evidence=False,
    )

    app.dependency_overrides[get_retrieval_service] = (
        lambda: retrieval_service
    )
    app.dependency_overrides[get_answer_generator] = (
        lambda: answer_generator
    )

    try:
        client = TestClient(app)

        response = client.post(
            "/v1/answer",
            json={
                "query": "What is the capital of Mars?",
            },
        )

        assert response.status_code == 200

        assert response.json() == {
            "query": "What is the capital of Mars?",
            "answer": (
                "The available documentation does not provide enough "
                "information to answer this question."
            ),
            "sources": [],
            "sufficient_evidence": False,
        }

    finally:
        app.dependency_overrides.clear()

def test_answer_returns_503_when_retrieval_is_unavailable() -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    answer_generator = MagicMock(spec=AnswerGenerator)

    retrieval_service.retrieve.side_effect = RetrievalUnavailableError(
        "Retrieval could not be completed."
    )

    app.dependency_overrides[get_retrieval_service] = (
        lambda: retrieval_service
    )
    app.dependency_overrides[get_answer_generator] = (
        lambda: answer_generator
    )

    try:
        client = TestClient(app)

        response = client.post(
            "/v1/answer",
            json={"query": "What is RAG?"},
        )

        assert response.status_code == 503
        assert response.json() == {
            "error": {
                "code": "answer_unavailable",
                "message": (
                    "Answer generation is temporarily unavailable."
                ),
                "details": [],
            }
        }

        answer_generator.generate.assert_not_called()

    finally:
        app.dependency_overrides.clear()
 
@pytest.mark.parametrize(
    "generation_error",
    [
        LanguageModelProviderError(
            "Language model request failed."
        ),
        CitationValidationError(
            "Generated citations were invalid."
        ),
        ContextBudgetError(
            budget_tokens=100,
            required_tokens=200,
        ),
    ],
)
def test_answer_returns_503_when_generation_fails(
    generation_error: Exception,
) -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    answer_generator = MagicMock(spec=AnswerGenerator)

    retrieval_results = [
        RetrievalResult(
            chunk=_chunk(),
            score=0.91,
        )
    ]

    retrieval_service.retrieve.return_value = retrieval_results
    answer_generator.generate.side_effect = generation_error

    app.dependency_overrides[get_retrieval_service] = (
        lambda: retrieval_service
    )
    app.dependency_overrides[get_answer_generator] = (
        lambda: answer_generator
    )

    try:
        client = TestClient(app)

        response = client.post(
            "/v1/answer",
            json={"query": "Why does retrieval fail?"},
        )

        assert response.status_code == 503
        assert response.json() == {
            "error": {
                "code": "answer_unavailable",
                "message": (
                    "Answer generation is temporarily unavailable."
                ),
                "details": [],
            }
        }

    finally:
        app.dependency_overrides.clear()

def test_answer_openapi_documents_service_unavailable_error() -> None:
    schema = app.openapi()

    answer_operation = schema["paths"]["/v1/answer"]["post"]

    unavailable_response = answer_operation["responses"]["503"]

    assert unavailable_response["description"] == (
        "Answer generation is temporarily unavailable."
    )

    error_schema = (
        unavailable_response["content"]["application/json"]["schema"]
    )

    assert error_schema == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
@pytest.mark.parametrize("query", ["", " ", "   \n\t"])
def test_answer_rejects_empty_query(query: str) -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/answer",
        json={"query": query},
    )

    assert response.status_code == 422


def test_answer_validation_does_not_build_retrieval_service() -> None:
    get_retrieval_service.cache_clear()
    get_answer_generator.cache_clear()

    try:
        with patch(
            "rag_service.api.dependencies.create_retrieval_service",
        ) as create_service:
            client = TestClient(app)

            response = client.post(
                "/v1/answer",
                json={"query": ""},
            )

        assert response.status_code == 422
        create_service.assert_not_called()
    finally:
        get_retrieval_service.cache_clear()
        get_answer_generator.cache_clear()


def test_answer_rejects_unsupported_filter() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/answer",
        json={
            "query": "What is RAG?",
            "filters": {
                "site_id": "the-doc-landscape",
            },
        },
    )

    assert response.status_code == 422

def test_answer_rejects_retrieval_limit() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/answer",
        json={
            "query": "What is RAG?",
            "limit": 10,
        },
    )

    assert response.status_code == 422

def test_answer_returns_standard_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/answer",
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

def test_answer_openapi_documents_validation_error() -> None:
    schema = app.openapi()

    answer_operation = schema["paths"]["/v1/answer"]["post"]

    validation_response = answer_operation["responses"]["422"]

    assert validation_response["description"] == (
        "Request validation failed."
    )

    error_schema = (
        validation_response["content"]["application/json"]["schema"]
    )

    assert error_schema == {
        "$ref": "#/components/schemas/ErrorResponse"
    }

def test_answer_openapi_documents_success_response() -> None:
    schema = app.openapi()

    answer_operation = schema["paths"]["/v1/answer"]["post"]

    success_schema = (
        answer_operation["responses"]["200"]
        ["content"]["application/json"]["schema"]
    )

    assert success_schema == {
        "$ref": "#/components/schemas/AnswerResponse"
    }