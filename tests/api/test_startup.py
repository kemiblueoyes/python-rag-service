import json
import logging
import socket
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from rag_service.api.app import app
from rag_service.api.dependencies import (
    get_answer_generator,
    get_retrieval_service,
)
from rag_service.api.startup import (
    StartupConfigurationError,
    validate_api_configuration,
)
from rag_service.config import settings
from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval import RetrievalService

CANARY = "corpus-canary-sk-secret"
STARTUP_LOGGER = "rag_service.api.startup"
ERROR_LOGGER = "rag_service.api.errors"
ANSWER_UNAVAILABLE = {
    "error": {
        "code": "answer_unavailable",
        "message": "Answer generation is temporarily unavailable.",
        "details": [],
    }
}


@pytest.fixture(autouse=True)
def clear_cached_services() -> Iterator[None]:
    get_answer_generator.cache_clear()
    get_retrieval_service.cache_clear()
    app.dependency_overrides.clear()
    yield
    get_answer_generator.cache_clear()
    get_retrieval_service.cache_clear()
    app.dependency_overrides.clear()


def _chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id="wordpress:page:1:chunk:0",
        document_id="wordpress:page:1",
        source="wordpress",
        source_id="1",
        title="Startup",
        url="https://example.test/startup",
        content_type="page",
        text=CANARY,
        heading_path=["Configuration"],
        sequence=0,
    )


def _valid_corpus() -> str:
    return json.dumps([_chunk().model_dump(mode="json")])


def _apply(
    monkeypatch: pytest.MonkeyPatch,
    corpus_path: Path,
    **overrides: Any,
) -> None:
    values: dict[str, Any] = {
        "rag_api_key": SecretStr("test-api-key"),
        "voyage_api_key": "voyage-test-key",
        "openai_api_key": "openai-test-key",
        "embedding_provider": "voyage",
        "embedding_model": "voyage-4-lite",
        "embedding_dimension": 1024,
        "vector_database": "qdrant",
        "qdrant_url": "http://localhost:6333",
        "qdrant_api_key": None,
        "qdrant_collection": "rag_chunks",
        "reranking_provider": "voyage",
        "reranking_model": "rerank-2.5",
        "retrieval_vector_candidate_depth": 20,
        "retrieval_lexical_candidate_depth": 20,
        "retrieval_fused_candidate_depth": 20,
        "retrieval_rrf_k": 60,
        "retrieval_support_cutoff": 0.70,
        "lexical_corpus_path": corpus_path,
        "generation_enabled": True,
        "generation_model": "gpt-5.6-terra",
        "generation_context_budget_tokens": 8_000,
        "generation_max_output_tokens": 1_000,
        "wordpress_base_url": None,
    }
    values.update(overrides)
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)


def _prepare(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    corpus_text: str | None = None,
    write_corpus: bool = True,
    **overrides: Any,
) -> Path:
    corpus_path = tmp_path / "chunks.json"
    if write_corpus:
        corpus_path.write_text(
            _valid_corpus() if corpus_text is None else corpus_text,
            encoding="utf-8",
        )
    _apply(monkeypatch, corpus_path, **overrides)
    return corpus_path


def _startup_error() -> StartupConfigurationError:
    try:
        with TestClient(app):
            pass
    except StartupConfigurationError as exc:
        return exc
    except BaseExceptionGroup as exc:
        matches = [
            item
            for item in exc.exceptions
            if isinstance(item, StartupConfigurationError)
        ]
        if len(matches) == 1:
            return matches[0]
        raise
    raise AssertionError("startup validation did not fail")


def _assert_safe_failure(
    caplog: pytest.LogCaptureFixture,
    error: StartupConfigurationError,
    settings_named: set[str],
) -> None:
    records = [record for record in caplog.records if record.name == STARTUP_LOGGER]
    assert {record.setting for record in records} == settings_named  # type: ignore[attr-defined]
    assert {failure.setting for failure in error.failures} == settings_named
    for record in records:
        assert record.levelno == logging.ERROR
        assert record.operation == "startup"  # type: ignore[attr-defined]
        assert record.reason == "invalid_configuration"  # type: ignore[attr-defined]
        assert record.exc_info is None
        assert CANARY not in record.getMessage()
        assert CANARY not in repr(record.__dict__)
    rendered = f"{error} {caplog.text}"
    assert CANARY not in rendered
    assert "voyage-test-key" not in rendered
    assert "openai-test-key" not in rendered
    assert "test-api-key" not in rendered


def _expect_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    settings_named: set[str],
    **overrides: Any,
) -> None:
    prepare_kwargs = {
        key: overrides.pop(key)
        for key in ("corpus_text", "write_corpus")
        if key in overrides
    }
    _prepare(monkeypatch, tmp_path, **prepare_kwargs, **overrides)
    with caplog.at_level(logging.ERROR):
        error = _startup_error()
    _assert_safe_failure(caplog, error, settings_named)


def test_api_starts_for_local_qdrant_without_wordpress_or_qdrant_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _prepare(
        monkeypatch,
        tmp_path,
        qdrant_api_key="",
        wordpress_base_url=None,
    )

    with caplog.at_level(logging.ERROR):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert not [record for record in caplog.records if record.name == STARTUP_LOGGER]
    assert CANARY not in caplog.text


def test_search_only_starts_without_openai_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _prepare(
        monkeypatch,
        tmp_path,
        generation_enabled=False,
        openai_api_key=None,
        generation_model="  ",
        generation_context_budget_tokens=0,
        generation_max_output_tokens=0,
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("field", "setting", "value"),
    [
        ("rag_api_key", "RAG_API_KEY", None),
        ("rag_api_key", "RAG_API_KEY", SecretStr("")),
        ("rag_api_key", "RAG_API_KEY", SecretStr(" \n\t")),
        ("voyage_api_key", "VOYAGE_API_KEY", None),
        ("voyage_api_key", "VOYAGE_API_KEY", ""),
        ("voyage_api_key", "VOYAGE_API_KEY", "  "),
        ("openai_api_key", "OPENAI_API_KEY", None),
        ("openai_api_key", "OPENAI_API_KEY", ""),
        ("openai_api_key", "OPENAI_API_KEY", "   "),
    ],
)
def test_startup_rejects_missing_and_blank_required_keys(
    field: str,
    setting: str,
    value: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _expect_startup_failure(
        monkeypatch,
        tmp_path,
        caplog,
        {setting},
        **{field: value},
    )


def test_startup_reports_each_missing_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _expect_startup_failure(
        monkeypatch,
        tmp_path,
        caplog,
        {"RAG_API_KEY", "VOYAGE_API_KEY"},
        rag_api_key=None,
        voyage_api_key=None,
    )


@pytest.mark.parametrize(
    ("field", "setting", "value"),
    [
        ("embedding_provider", "EMBEDDING_PROVIDER", "cohere"),
        ("reranking_provider", "RERANKING_PROVIDER", "cohere"),
        ("vector_database", "VECTOR_DATABASE", "pinecone"),
        ("embedding_model", "EMBEDDING_MODEL", " "),
        ("reranking_model", "RERANKING_MODEL", ""),
        ("qdrant_url", "QDRANT_URL", "  "),
        ("qdrant_collection", "QDRANT_COLLECTION", ""),
        ("generation_model", "GENERATION_MODEL", " "),
    ],
)
def test_startup_rejects_unsupported_providers_and_blank_names(
    field: str,
    setting: str,
    value: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _expect_startup_failure(
        monkeypatch,
        tmp_path,
        caplog,
        {setting},
        **{field: value},
    )


@pytest.mark.parametrize(
    ("field", "setting", "value"),
    [
        ("retrieval_vector_candidate_depth", "RETRIEVAL_VECTOR_CANDIDATE_DEPTH", 0),
        ("retrieval_vector_candidate_depth", "RETRIEVAL_VECTOR_CANDIDATE_DEPTH", -1),
        ("retrieval_lexical_candidate_depth", "RETRIEVAL_LEXICAL_CANDIDATE_DEPTH", 0),
        ("retrieval_fused_candidate_depth", "RETRIEVAL_FUSED_CANDIDATE_DEPTH", 0),
        ("retrieval_rrf_k", "RETRIEVAL_RRF_K", 0),
        ("embedding_dimension", "EMBEDDING_DIMENSION", 0),
        ("embedding_dimension", "EMBEDDING_DIMENSION", -5),
        ("retrieval_support_cutoff", "RETRIEVAL_SUPPORT_CUTOFF", -0.01),
        ("retrieval_support_cutoff", "RETRIEVAL_SUPPORT_CUTOFF", 1.01),
        ("generation_context_budget_tokens", "GENERATION_CONTEXT_BUDGET_TOKENS", 0),
        ("generation_max_output_tokens", "GENERATION_MAX_OUTPUT_TOKENS", 0),
    ],
)
def test_startup_rejects_invalid_numeric_settings(
    field: str,
    setting: str,
    value: float,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _expect_startup_failure(
        monkeypatch,
        tmp_path,
        caplog,
        {setting},
        **{field: value},
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"retrieval_support_cutoff": 0.0},
        {"retrieval_support_cutoff": 1.0},
        {
            "retrieval_vector_candidate_depth": 1,
            "retrieval_lexical_candidate_depth": 1,
            "retrieval_fused_candidate_depth": 1,
            "retrieval_rrf_k": 1,
        },
        {
            "embedding_dimension": 1,
            "generation_context_budget_tokens": 1,
            "generation_max_output_tokens": 1,
        },
    ],
)
def test_startup_accepts_numeric_boundaries(
    overrides: dict[str, float],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _prepare(monkeypatch, tmp_path, **overrides)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_startup_rejects_missing_corpus(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _expect_startup_failure(
        monkeypatch,
        tmp_path,
        caplog,
        {"LEXICAL_CORPUS_PATH"},
        write_corpus=False,
    )
    assert "readable file" in _last_message(caplog)


def test_startup_rejects_unreadable_corpus(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    corpus_path = _prepare(monkeypatch, tmp_path)
    corpus_path.chmod(0)
    try:
        with caplog.at_level(logging.ERROR):
            error = _startup_error()
        _assert_safe_failure(caplog, error, {"LEXICAL_CORPUS_PATH"})
        assert "readable" in error.failures[0].message
    finally:
        corpus_path.chmod(0o600)


def test_startup_rejects_malformed_corpus(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _expect_startup_failure(
        monkeypatch,
        tmp_path,
        caplog,
        {"LEXICAL_CORPUS_PATH"},
        corpus_text="{" + CANARY,
    )
    assert "valid JSON" in _last_message(caplog)


def test_startup_rejects_invalid_chunk_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _expect_startup_failure(
        monkeypatch,
        tmp_path,
        caplog,
        {"LEXICAL_CORPUS_PATH"},
        corpus_text=json.dumps([{"text": CANARY}]),
    )
    assert "invalid chunk" in _last_message(caplog)


def test_startup_rejects_empty_corpus(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _expect_startup_failure(
        monkeypatch,
        tmp_path,
        caplog,
        {"LEXICAL_CORPUS_PATH"},
        corpus_text="[]",
    )
    assert "at least one chunk" in _last_message(caplog)


def test_startup_rejects_non_list_corpus(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _expect_startup_failure(
        monkeypatch,
        tmp_path,
        caplog,
        {"LEXICAL_CORPUS_PATH"},
        corpus_text=json.dumps({"text": CANARY}),
    )
    assert "JSON list" in _last_message(caplog)


def test_startup_validation_makes_no_external_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _prepare(
        monkeypatch,
        tmp_path,
        qdrant_url="https://qdrant.example.invalid:6333",
        qdrant_api_key=None,
        wordpress_base_url=None,
    )

    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("startup validation opened a network connection")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket, "getaddrinfo", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)

    with (
        patch(
            "rag_service.vectorstores.qdrant.QdrantClient",
            side_effect=AssertionError("Qdrant client constructed"),
        ),
        patch(
            "rag_service.generation.providers.openai.OpenAI",
            side_effect=AssertionError("OpenAI client constructed"),
        ),
        patch(
            "voyageai.client.Client",
            side_effect=AssertionError("Voyage client constructed"),
        ),
        patch(
            "rag_service.connectors.wordpress.client.WordPressClient",
            side_effect=AssertionError("WordPress client constructed"),
        ),
    ):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "url",
    [
        "localhost:6333",
        "ftp://localhost:6333",
        "http://",
        "http:///missing-host",
        "http://localhost:abc",
        "http://localhost:70000",
        "http://localhost:0",
        "http://256.1.1.1:6333",
        "http://bad host:6333",
        " http://localhost:6333",
        f"http://localhost:{CANARY}",
    ],
)
def test_startup_rejects_malformed_qdrant_urls(
    url: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _prepare(monkeypatch, tmp_path, qdrant_url=url)
    _block_network(monkeypatch)

    with caplog.at_level(logging.ERROR):
        error = _startup_error()

    _assert_safe_failure(caplog, error, {"QDRANT_URL"})
    message = _last_message(caplog)
    assert "HTTP or HTTPS URL" in message
    assert url not in message
    assert url not in str(error)
    assert CANARY not in message


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:6333",
        "http://127.0.0.1:6333",
        "http://[::1]:6333",
        "HTTP://localhost:6333",
        "https://your-cluster.cloud.qdrant.io",
        "https://your-cluster.cloud.qdrant.io:6333",
    ],
)
def test_startup_accepts_local_and_hosted_qdrant_urls(
    url: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _prepare(monkeypatch, tmp_path, qdrant_url=url)
    _block_network(monkeypatch)

    with (
        patch(
            "rag_service.vectorstores.qdrant.QdrantClient",
            side_effect=AssertionError("Qdrant client constructed"),
        ),
        patch(
            "rag_service.generation.providers.openai.OpenAI",
            side_effect=AssertionError("OpenAI client constructed"),
        ),
        patch(
            "voyageai.client.Client",
            side_effect=AssertionError("Voyage client constructed"),
        ),
        patch(
            "rag_service.connectors.wordpress.client.WordPressClient",
            side_effect=AssertionError("WordPress client constructed"),
        ),
    ):
        validate_api_configuration(settings)


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("startup validation opened a network connection")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket, "getaddrinfo", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)


def test_openapi_does_not_require_credentials_or_corpus(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _prepare(
        monkeypatch,
        tmp_path,
        write_corpus=False,
        rag_api_key=None,
        voyage_api_key=None,
        openai_api_key=None,
    )

    schema = app.openapi()

    assert "/health" in schema["paths"]
    assert "/v1/search" in schema["paths"]
    assert "/v1/answer" in schema["paths"]


def test_disabled_generation_returns_answer_unavailable_without_providers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _prepare(
        monkeypatch,
        tmp_path,
        generation_enabled=False,
        openai_api_key=None,
    )
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.return_value = []
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval

    with (
        patch(
            "rag_service.api.dependencies.create_answer_generator",
        ) as create_generator,
        patch(
            "rag_service.api.dependencies.create_retrieval_service",
        ) as create_retrieval,
        patch(
            "rag_service.vectorstores.qdrant.QdrantClient",
        ) as qdrant,
        patch(
            "rag_service.generation.providers.openai.OpenAI",
        ) as openai_client,
        patch("voyageai.client.Client") as voyage,
        patch(
            "rag_service.connectors.wordpress.client.WordPressClient",
        ) as wordpress,
    ):
        with TestClient(app) as client:
            missing_key = client.post(
                "/v1/answer",
                json={"query": CANARY},
            )
            invalid = client.post(
                "/v1/answer",
                json={"query": CANARY, "limit": 1},
                headers=api_key_headers,
            )
            with caplog.at_level(logging.ERROR, logger=ERROR_LOGGER):
                disabled = client.post(
                    "/v1/answer",
                    json={"query": CANARY},
                    headers=api_key_headers,
                )
            search = client.post(
                "/v1/search",
                json={"query": "What is RAG?"},
                headers=api_key_headers,
            )

    assert missing_key.status_code == 401
    assert missing_key.json()["error"]["code"] == "authentication_failed"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert disabled.status_code == 503
    assert disabled.json() == ANSWER_UNAVAILABLE
    assert search.status_code == 200
    assert search.json() == {"query": "What is RAG?", "results": []}

    records = [record for record in caplog.records if record.name == ERROR_LOGGER]
    assert len(records) == 1
    assert records[0].operation == "generation"  # type: ignore[attr-defined]
    assert records[0].reason == "generation_disabled"  # type: ignore[attr-defined]
    assert records[0].exc_info is None
    assert CANARY not in records[0].getMessage()
    assert CANARY not in repr(records[0].__dict__)

    retrieval.retrieve.assert_called_once()
    create_generator.assert_not_called()
    create_retrieval.assert_not_called()
    qdrant.assert_not_called()
    openai_client.assert_not_called()
    voyage.assert_not_called()
    wordpress.assert_not_called()


def _last_message(caplog: pytest.LogCaptureFixture) -> str:
    records = [record for record in caplog.records if record.name == STARTUP_LOGGER]
    assert len(records) == 1
    return records[0].getMessage()
