import asyncio
import json
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from rag_service.api.app import app
from rag_service.api.dependencies import (
    get_answer_generator,
    get_retrieval_service,
)
from rag_service.api.limits import (
    FILTER_LIST_MAX_ENTRIES,
    FILTER_VALUE_MAX_CHARACTERS,
    QUERY_MAX_CHARACTERS,
    REQUEST_BODY_MAX_BYTES,
    REQUEST_TOO_LARGE_MESSAGE,
    SEARCH_LIMIT_DEFAULT,
    SEARCH_LIMIT_MAX,
)
from rag_service.config import settings
from rag_service.retrieval import RetrievalService

CANARY = "sk-secret-request-limit"
PATHS = ("/v1/search", "/v1/answer")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _no_providers() -> Iterator[tuple[MagicMock, ...]]:
    with (
        patch(
            "rag_service.api.dependencies.create_retrieval_service",
        ) as create_retrieval,
        patch(
            "rag_service.api.dependencies.create_answer_generator",
        ) as create_answer,
        patch("voyageai.client.Client") as voyage,
        patch("rag_service.vectorstores.qdrant.QdrantClient") as qdrant,
        patch("rag_service.generation.providers.openai.OpenAI") as openai,
        patch("rag_service.lexical.factory.Bm25Retriever") as bm25,
    ):
        yield (
            create_retrieval,
            create_answer,
            voyage,
            qdrant,
            openai,
            bm25,
        )


@pytest.fixture
def idle_providers() -> Iterator[tuple[MagicMock, ...]]:
    yield from _no_providers()


def _assert_idle(providers: tuple[MagicMock, ...]) -> None:
    for provider in providers:
        provider.assert_not_called()


def _assert_safe(response_text: str, caplog: pytest.LogCaptureFixture) -> None:
    for secret in (CANARY, "Traceback", "ValidationError"):
        assert secret not in response_text
        assert secret not in caplog.text


def _too_large_body() -> dict[str, Any]:
    return {
        "error": {
            "code": "request_too_large",
            "message": REQUEST_TOO_LARGE_MESSAGE,
            "details": [],
        }
    }


def _post_asgi(
    path: str,
    chunks: list[bytes],
    *,
    headers: dict[str, str],
    content_length: int | None,
) -> tuple[int, bytes]:
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    pending = list(chunks)

    async def receive() -> dict[str, Any]:
        if not pending:
            return {"type": "http.disconnect"}
        body = pending.pop(0)
        return {
            "type": "http.request",
            "body": body,
            "more_body": bool(pending),
        }

    raw_headers = [
        (b"content-type", b"application/json"),
        *[
            (name.lower().encode("latin-1"), value.encode("latin-1"))
            for name, value in headers.items()
        ],
    ]
    if content_length is not None:
        raw_headers.append(
            (b"content-length", str(content_length).encode("ascii")),
        )
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }
    asyncio.run(app(scope, receive, send))
    status = next(
        message["status"]
        for message in sent
        if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    return status, body


def _mock_search() -> MagicMock:
    service = MagicMock(spec=RetrievalService)
    service.retrieve.return_value = []
    app.dependency_overrides[get_retrieval_service] = lambda: service
    return service


@pytest.mark.parametrize("path", PATHS)
def test_query_character_limit(
    path: str,
    client: TestClient,
    api_key_headers: dict[str, str],
    idle_providers: tuple[MagicMock, ...],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accepted = " " + ("é" * QUERY_MAX_CHARACTERS) + "\n"
    combining = "  " + ("a" * (QUERY_MAX_CHARACTERS - 2)) + "e\u0301" + "\t"
    assert len(combining.strip()) == QUERY_MAX_CHARACTERS
    if path == "/v1/answer":
        monkeypatch.setattr(settings, "generation_enabled", False)
        get_answer_generator.cache_clear()
    service = _mock_search()
    try:
        for query in (accepted, combining):
            response = client.post(
                path,
                json={"query": query},
                headers=api_key_headers,
            )
            if path == "/v1/answer":
                assert response.status_code == 503
                assert response.json()["error"]["code"] == "answer_unavailable"
            else:
                assert response.status_code == 200
                assert service.retrieve.call_args.args[0].query == query.strip()
    finally:
        app.dependency_overrides.clear()
        get_answer_generator.cache_clear()

    response = client.post(
        path,
        json={"query": " " + ("é" * (QUERY_MAX_CHARACTERS + 1)) + CANARY},
        headers=api_key_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"][0]["field"] == "query"
    assert body["error"]["details"][0]["message"] == (
        "String should have at most 2000 characters"
    )
    _assert_safe(response.text, caplog)
    _assert_idle(idle_providers)


def test_search_limit_bounds_and_default(
    client: TestClient,
    api_key_headers: dict[str, str],
    idle_providers: tuple[MagicMock, ...],
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = _mock_search()
    try:
        for limit in (1, SEARCH_LIMIT_MAX):
            response = client.post(
                "/v1/search",
                json={"query": "What is RAG?", "limit": limit},
                headers=api_key_headers,
            )
            assert response.status_code == 200
            assert service.retrieve.call_args.args[0].limit == limit
        omitted = client.post(
            "/v1/search",
            json={"query": "What is RAG?"},
            headers=api_key_headers,
        )
        assert omitted.status_code == 200
        assert service.retrieve.call_args.args[0].limit == SEARCH_LIMIT_DEFAULT
    finally:
        app.dependency_overrides.clear()

    response = client.post(
        "/v1/search",
        json={"query": "What is RAG?", "limit": SEARCH_LIMIT_MAX + 1},
        headers=api_key_headers,
    )
    assert response.status_code == 422
    detail = response.json()["error"]["details"][0]
    assert detail["field"] == "limit"
    assert detail["message"] == "Input should be less than or equal to 20"
    _assert_safe(response.text, caplog)
    _assert_idle(idle_providers)


@pytest.mark.parametrize("path", PATHS)
def test_filter_value_and_list_limits(
    path: str,
    client: TestClient,
    api_key_headers: dict[str, str],
    idle_providers: tuple[MagicMock, ...],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accepted_value = " " + ("w" * FILTER_VALUE_MAX_CHARACTERS) + " "
    accepted_list = [f"id-{index}" for index in range(FILTER_LIST_MAX_ENTRIES)]
    if path == "/v1/answer":
        monkeypatch.setattr(settings, "generation_enabled", False)
        get_answer_generator.cache_clear()
    service = _mock_search()
    try:
        response = client.post(
            path,
            json={
                "query": "What is RAG?",
                "filters": {
                    "source": accepted_value,
                    "content_type": accepted_list,
                },
            },
            headers=api_key_headers,
        )
        if path == "/v1/search":
            assert response.status_code == 200
            filters = service.retrieve.call_args.args[0].filters
            assert filters["source"] == accepted_value.strip()
            assert filters["content_type"] == accepted_list
        else:
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "answer_unavailable"
    finally:
        app.dependency_overrides.clear()
        get_answer_generator.cache_clear()

    long_value = client.post(
        path,
        json={
            "query": "What is RAG?",
            "filters": {"source": "w" * (FILTER_VALUE_MAX_CHARACTERS + 1) + CANARY},
        },
        headers=api_key_headers,
    )
    assert long_value.status_code == 422
    assert long_value.json()["error"]["details"][0]["field"] == "filters.source"
    assert long_value.json()["error"]["details"][0]["message"] == (
        "String should have at most 256 characters"
    )

    long_list = client.post(
        path,
        json={
            "query": "What is RAG?",
            "filters": {
                "content_type": ["page"] * (FILTER_LIST_MAX_ENTRIES + 1),
            },
        },
        headers=api_key_headers,
    )
    assert long_list.status_code == 422
    assert long_list.json()["error"]["details"][0]["field"] == "filters.content_type"
    assert "at most 50" in long_list.json()["error"]["details"][0]["message"]

    blank = client.post(
        path,
        json={"query": "What is RAG?", "filters": {"source": "  \n"}},
        headers=api_key_headers,
    )
    assert blank.status_code == 422
    unknown = client.post(
        path,
        json={"query": "What is RAG?", "filters": {"site_id": "extra"}},
        headers=api_key_headers,
    )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["details"][0]["field"] == "filters.site_id"
    _assert_safe(long_value.text + long_list.text, caplog)
    _assert_idle(idle_providers)


@pytest.mark.parametrize("path", PATHS)
def test_oversized_body_with_content_length_returns_413(
    path: str,
    client: TestClient,
    api_key_headers: dict[str, str],
    idle_providers: tuple[MagicMock, ...],
    caplog: pytest.LogCaptureFixture,
) -> None:
    body = CANARY.encode() + b"x" * (REQUEST_BODY_MAX_BYTES + 1)
    response = client.post(
        path,
        content=body,
        headers={**api_key_headers, "Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json() == _too_large_body()
    assert int(response.request.headers["content-length"]) == len(body)
    _assert_safe(response.text, caplog)
    _assert_idle(idle_providers)


@pytest.mark.parametrize("path", PATHS)
def test_oversized_body_without_content_length_returns_413(
    path: str,
    api_key_headers: dict[str, str],
    idle_providers: tuple[MagicMock, ...],
    caplog: pytest.LogCaptureFixture,
) -> None:
    body = CANARY.encode() + b"y" * (REQUEST_BODY_MAX_BYTES + 1)
    status, payload = _post_asgi(
        path,
        [body],
        headers=api_key_headers,
        content_length=None,
    )
    assert status == 413
    assert json.loads(payload) == _too_large_body()
    _assert_safe(payload.decode(), caplog)
    _assert_idle(idle_providers)


@pytest.mark.parametrize("path", PATHS)
def test_chunked_body_that_crosses_the_limit_returns_413(
    path: str,
    api_key_headers: dict[str, str],
    idle_providers: tuple[MagicMock, ...],
    caplog: pytest.LogCaptureFixture,
) -> None:
    first = CANARY.encode() + b"a" * 40_000
    second = b"b" * 40_000
    assert len(first) <= REQUEST_BODY_MAX_BYTES
    assert len(first) + len(second) > REQUEST_BODY_MAX_BYTES
    status, payload = _post_asgi(
        path,
        [first, second],
        headers=api_key_headers,
        content_length=len(first),
    )
    assert status == 413
    assert json.loads(payload) == _too_large_body()
    _assert_safe(payload.decode(), caplog)
    _assert_idle(idle_providers)


def test_declared_content_length_does_not_replace_the_byte_count(
    api_key_headers: dict[str, str],
) -> None:
    service = _mock_search()
    try:
        status, payload = _post_asgi(
            "/v1/search",
            [b'{"query":"short"}'],
            headers=api_key_headers,
            content_length=REQUEST_BODY_MAX_BYTES + 1,
        )
        assert status == 200
        assert json.loads(payload)["results"] == []
        service.retrieve.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_body_at_the_limit_can_still_be_a_normal_request(
    api_key_headers: dict[str, str],
) -> None:
    prefix = b'{"query":"boundary"}'
    body = prefix + b" " * (REQUEST_BODY_MAX_BYTES - len(prefix))
    assert len(body) == REQUEST_BODY_MAX_BYTES
    service = _mock_search()
    try:
        status, payload = _post_asgi(
            "/v1/search",
            [body[:100], body[100:20_000], body[20_000:]],
            headers=api_key_headers,
            content_length=None,
        )
        assert status == 200
        assert json.loads(payload)["query"] == "boundary"
        service.retrieve.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_health_and_search_only_stay_available(
    client: TestClient,
    api_key_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    idle_providers: tuple[MagicMock, ...],
) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    oversized = b"z" * (REQUEST_BODY_MAX_BYTES + 1)
    other = client.post("/health", content=oversized)
    assert other.status_code != 413

    service = _mock_search()
    try:
        search = client.post(
            "/v1/search",
            json={"query": "What is RAG?"},
            headers=api_key_headers,
        )
        assert search.status_code == 200
        service.retrieve.assert_called_once()
    finally:
        app.dependency_overrides.clear()

    monkeypatch.setattr(settings, "generation_enabled", False)
    get_answer_generator.cache_clear()
    answer = client.post(
        "/v1/answer",
        json={"query": "What is RAG?"},
        headers=api_key_headers,
    )
    assert answer.status_code == 503
    assert answer.json()["error"]["code"] == "answer_unavailable"
    _assert_idle(idle_providers)
    get_answer_generator.cache_clear()


def test_cancelled_body_read_is_not_an_http_error() -> None:
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    async def receive() -> dict[str, Any]:
        raise asyncio.CancelledError

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/v1/search",
        "raw_path": b"/v1/search",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(app(scope, receive, send))
    assert sent == []


def test_openapi_exposes_field_limits_and_request_too_large() -> None:
    schema = app.openapi()
    search = schema["components"]["schemas"]["SearchRequest"]
    answer = schema["components"]["schemas"]["AnswerRequest"]
    filters = schema["components"]["schemas"]["SearchFilters"]
    assert search["properties"]["query"]["maxLength"] == QUERY_MAX_CHARACTERS
    assert search["properties"]["query"]["minLength"] == 1
    assert answer["properties"]["query"]["maxLength"] == QUERY_MAX_CHARACTERS
    assert search["properties"]["limit"]["minimum"] == 1
    assert search["properties"]["limit"]["maximum"] == SEARCH_LIMIT_MAX
    assert search["properties"]["limit"]["default"] == SEARCH_LIMIT_DEFAULT
    encoded = json.dumps(filters)
    assert '"maxLength": 256' in encoded
    assert '"maxItems": 50' in encoded
    for path in PATHS:
        response = schema["paths"][path]["post"]["responses"]["413"]
        assert response["description"] == "The request body is too large."
        example = response["content"]["application/json"]["examples"]
        assert example["request_too_large"]["value"] == _too_large_body()
