import asyncio
import logging
from collections.abc import Iterator
from concurrent.futures import CancelledError
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from httpx import Headers
from openai import APIConnectionError, AuthenticationError
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)
from voyageai.error import APIConnectionError as VoyageConnectionError
from voyageai.error import AuthenticationError as VoyageAuthenticationError

from rag_service.api.app import app
from rag_service.api.dependencies import get_answer_generator, get_retrieval_service
from rag_service.config import settings
from rag_service.generation.models import GenerationPrompt
from rag_service.generation.providers.openai import OpenAILanguageModel
from rag_service.retrieval import RetrievalService

CANARY = "private-query sk-secret https://user:password@qdrant.example/collection"
LOGGER = "rag_service.api.errors"


@pytest.fixture(autouse=True)
def isolate_dependencies() -> Iterator[None]:
    app.dependency_overrides.clear()
    get_answer_generator.cache_clear()
    get_retrieval_service.cache_clear()
    yield
    app.dependency_overrides.clear()
    get_answer_generator.cache_clear()
    get_retrieval_service.cache_clear()


def _retrieval_service(failure: BaseException) -> RetrievalService:
    embedding = MagicMock()
    embedding.embed_query.side_effect = failure
    return RetrievalService(
        embedding_provider=embedding,
        vector_store=MagicMock(),
        lexical_retriever=MagicMock(),
        reranker=MagicMock(),
    )


def _qdrant_retrieval(failure: BaseException) -> RetrievalService:
    embedding = MagicMock()
    embedding.embed_query.return_value = [0.1, 0.2]
    vector_store = MagicMock()
    vector_store.search.side_effect = failure
    return RetrievalService(
        embedding_provider=embedding,
        vector_store=vector_store,
        lexical_retriever=MagicMock(),
        reranker=MagicMock(),
    )


def _assert_safe(
    response: httpx.Response,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    *,
    reason: str,
) -> None:
    captured = capsys.readouterr()
    assert CANARY not in response.text
    assert "test-api-key" not in response.text
    assert CANARY not in caplog.text
    assert CANARY not in captured.err
    assert CANARY not in captured.out
    assert all(record.exc_info is None for record in caplog.records)
    assert all(record.stack_info is None for record in caplog.records)
    matches = [
        record
        for record in caplog.records
        if getattr(record, "reason", None) == reason
    ]
    assert len(matches) == 1
    assert CANARY not in repr(matches[0].__dict__)


def test_invalid_request_does_not_construct_dependencies(
    api_key_headers: dict[str, str],
) -> None:
    with (
        patch(
            "rag_service.api.dependencies.create_retrieval_service",
        ) as create_retrieval,
        patch(
            "rag_service.api.dependencies.create_answer_generator",
        ) as create_generator,
    ):
        client = TestClient(app)
        search = client.post(
            "/v1/search",
            json={"query": ""},
            headers=api_key_headers,
        )
        answer = client.post(
            "/v1/answer",
            json={"query": "What is RAG?", "limit": 1},
            headers=api_key_headers,
        )

    assert search.status_code == 422
    assert search.json()["error"]["code"] == "validation_error"
    assert answer.status_code == 422
    assert answer.json()["error"]["code"] == "validation_error"
    create_retrieval.assert_not_called()
    create_generator.assert_not_called()


def test_missing_api_key_stays_unauthorized() -> None:
    response = TestClient(app).post("/v1/search", json={"query": "What is RAG?"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_failed"


def test_search_only_skips_answer_generator(
    api_key_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "generation_enabled", False)
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.return_value = []
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    get_answer_generator.cache_clear()

    with patch(
        "rag_service.api.dependencies.create_answer_generator",
    ) as create_generator:
        client = TestClient(app)
        answer = client.post(
            "/v1/answer",
            json={"query": "What is RAG?"},
            headers=api_key_headers,
        )
        search = client.post(
            "/v1/search",
            json={"query": "What is RAG?"},
            headers=api_key_headers,
        )

    assert answer.status_code == 503
    assert answer.json()["error"]["code"] == "answer_unavailable"
    assert search.status_code == 200
    assert search.json() == {"query": "What is RAG?", "results": []}
    create_generator.assert_not_called()


def test_retrieval_construction_failure_is_configuration_error(
    api_key_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    corpus = tmp_path / "chunks.json"
    corpus.write_text(CANARY, encoding="utf-8")
    monkeypatch.setattr(settings, "lexical_corpus_path", corpus)

    with (
        caplog.at_level(logging.DEBUG),
        patch("voyageai.client.Client"),
        patch("rag_service.vectorstores.qdrant.QdrantClient"),
    ):
        response = TestClient(app).post(
            "/v1/search",
            json={"query": "What is RAG?"},
            headers=api_key_headers,
        )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "configuration_error",
            "message": "The service configuration is invalid.",
            "details": [],
        }
    }
    _assert_safe(response, caplog, capsys, reason="invalid_lexical_corpus")


def test_answer_generator_construction_failure_is_configuration_error(
    api_key_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(settings, "generation_enabled", True)
    monkeypatch.setattr(settings, "generation_model", CANARY)
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.return_value = []
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    get_answer_generator.cache_clear()

    with caplog.at_level(logging.DEBUG):
        response = TestClient(app).post(
            "/v1/answer",
            json={"query": "What is RAG?"},
            headers=api_key_headers,
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "configuration_error"
    _assert_safe(response, caplog, capsys, reason="unrecognized_generation_model")


@pytest.mark.parametrize(
    ("failure", "status", "code", "reason"),
    [
        (
            VoyageConnectionError(CANARY),
            503,
            "retrieval_unavailable",
            "retrieval_dependency_failed",
        ),
        (
            UnexpectedResponse(
                status_code=503,
                reason_phrase=CANARY,
                content=CANARY.encode(),
                headers=Headers(),
            ),
            503,
            "retrieval_unavailable",
            "retrieval_dependency_failed",
        ),
        (
            VoyageAuthenticationError(CANARY),
            500,
            "configuration_error",
            "provider_configuration_rejected",
        ),
        (
            UnexpectedResponse(
                status_code=401,
                reason_phrase=CANARY,
                content=CANARY.encode(),
                headers=Headers(),
            ),
            500,
            "configuration_error",
            "provider_configuration_rejected",
        ),
        (ValueError(CANARY), 500, "internal_error", "unexpected_failure"),
        (RuntimeError(CANARY), 500, "internal_error", "unexpected_failure"),
    ],
)
def test_search_classifies_provider_and_programming_failures(
    failure: BaseException,
    status: int,
    code: str,
    reason: str,
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app.dependency_overrides[get_retrieval_service] = lambda: _retrieval_service(
        failure
    )

    with caplog.at_level(logging.DEBUG):
        response = TestClient(app).post(
            "/v1/search",
            json={"query": CANARY},
            headers=api_key_headers,
        )

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == []
    _assert_safe(response, caplog, capsys, reason=reason)


def test_answer_keeps_temporary_provider_failure(
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    model = OpenAILanguageModel(
        client=MagicMock(),
        model="gpt-5.6-terra",
        api_key="test-key",
    )
    model._client.responses.parse.side_effect = APIConnectionError(  # type: ignore[attr-defined]
        message=CANARY,
        request=request,
    )
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.return_value = []
    generator = MagicMock()

    def generate(**_kwargs: object) -> None:
        model.generate(
            GenerationPrompt(system_message=CANARY, user_message=CANARY)
        )

    generator.generate.side_effect = generate
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    app.dependency_overrides[get_answer_generator] = lambda: generator

    with caplog.at_level(logging.DEBUG):
        response = TestClient(app).post(
            "/v1/answer",
            json={"query": CANARY},
            headers=api_key_headers,
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "answer_unavailable"
    _assert_safe(response, caplog, capsys, reason="provider_request_failed")


def test_answer_provider_configuration_failure_is_500(
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response_http = httpx.Response(401, request=request)
    model = OpenAILanguageModel(
        client=MagicMock(),
        model="gpt-5.6-terra",
        api_key="test-key",
    )
    model._client.responses.parse.side_effect = AuthenticationError(  # type: ignore[attr-defined]
        CANARY,
        response=response_http,
        body=CANARY,
    )
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.return_value = []
    generator = MagicMock()

    def generate(**_kwargs: object) -> None:
        model.generate(
            GenerationPrompt(system_message=CANARY, user_message=CANARY)
        )

    generator.generate.side_effect = generate
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    app.dependency_overrides[get_answer_generator] = lambda: generator

    with caplog.at_level(logging.DEBUG):
        response = TestClient(app).post(
            "/v1/answer",
            json={"query": CANARY},
            headers=api_key_headers,
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "configuration_error"
    _assert_safe(
        response,
        caplog,
        capsys,
        reason="provider_configuration_rejected",
    )


def test_cancellation_is_not_converted_to_an_error_response(
    api_key_headers: dict[str, str],
) -> None:
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.side_effect = asyncio.CancelledError()
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval

    with pytest.raises(CancelledError):
        TestClient(app).post(
            "/v1/search",
            json={"query": "What is RAG?"},
            headers=api_key_headers,
        )


@pytest.mark.parametrize(
    "failure",
    [
        ExceptionGroup(CANARY, [ValueError(CANARY), RuntimeError(CANARY)]),
        ExceptionGroup(
            CANARY,
            [ExceptionGroup(CANARY, [RuntimeError(CANARY)])],
        ),
    ],
)
def test_exception_groups_return_internal_error(
    failure: ExceptionGroup[Exception],
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.side_effect = failure
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval

    with caplog.at_level(logging.DEBUG):
        response = TestClient(app).post(
            "/v1/search",
            json={"query": CANARY},
            headers=api_key_headers,
        )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "The service couldn't complete the request.",
            "details": [],
        }
    }
    _assert_safe(response, caplog, capsys, reason="unexpected_failure")


@pytest.mark.parametrize(
    "failure",
    [
        BaseExceptionGroup(CANARY, [asyncio.CancelledError()]),
        ExceptionGroup(CANARY, [CancelledError()]),
    ],
)
def test_grouped_cancellation_is_not_converted(
    failure: BaseExceptionGroup,
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.side_effect = failure
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval

    with (
        caplog.at_level(logging.DEBUG),
        pytest.raises((CancelledError, BaseExceptionGroup)),
    ):
        TestClient(app).post(
            "/v1/search",
            json={"query": "What is RAG?"},
            headers=api_key_headers,
        )

    assert not [
        record
        for record in caplog.records
        if getattr(record, "reason", None) == "unexpected_failure"
    ]


def test_grouped_shutdown_is_not_converted(
    api_key_headers: dict[str, str],
) -> None:
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.side_effect = BaseExceptionGroup(
        "shutdown",
        [KeyboardInterrupt()],
    )
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval

    with pytest.raises(BaseExceptionGroup):
        TestClient(app).post(
            "/v1/search",
            json={"query": "What is RAG?"},
            headers=api_key_headers,
        )


@pytest.mark.parametrize("path", ["/v1/search", "/v1/answer"])
@pytest.mark.parametrize(
    ("failure", "temporary"),
    [
        (ResourceExhaustedResponse(CANARY, 1), True),
        (ResponseHandlingException(httpx.ConnectError(CANARY)), True),
        (ResponseHandlingException(httpx.ReadTimeout(CANARY)), True),
        (ResponseHandlingException(ValueError(CANARY)), False),
        (ResponseHandlingException(RuntimeError(CANARY)), False),
    ],
)
def test_qdrant_failures_are_classified_for_search_and_answer(
    path: str,
    failure: BaseException,
    temporary: bool,
    api_key_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(settings, "generation_enabled", True)
    app.dependency_overrides[get_retrieval_service] = lambda: _qdrant_retrieval(
        failure
    )
    if temporary and path == "/v1/search":
        status, code, reason = (
            503,
            "retrieval_unavailable",
            "retrieval_dependency_failed",
        )
    elif temporary:
        status, code, reason = (
            503,
            "answer_unavailable",
            "retrieval_dependency_failed",
        )
    else:
        status, code, reason = (500, "internal_error", "unexpected_failure")

    with caplog.at_level(logging.DEBUG):
        response = TestClient(app).post(
            path,
            json={"query": CANARY},
            headers=api_key_headers,
        )

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == []
    _assert_safe(response, caplog, capsys, reason=reason)
