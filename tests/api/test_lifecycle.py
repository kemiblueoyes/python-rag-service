import json
import threading
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from rag_service.api.app import app
from rag_service.api.dependencies import (
    get_answer_generator,
    get_retrieval_service,
    shutdown_api_dependencies,
)
from rag_service.config import settings
from rag_service.lexical.bm25 import Bm25Retriever
from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval.models import RetrievalRequest


@pytest.fixture(autouse=True)
def clear_cached_services() -> Iterator[None]:
    get_answer_generator.cache_clear()
    get_retrieval_service.cache_clear()
    app.dependency_overrides.clear()
    yield
    shutdown_api_dependencies()
    get_answer_generator.cache_clear()
    get_retrieval_service.cache_clear()
    app.dependency_overrides.clear()


class _GateLock:
    """Block the first holder until the test releases it."""

    def __init__(self) -> None:
        self._cv = threading.Condition()
        self._held = False
        self.waiters = 0
        self._hold_first = True
        self.entered = threading.Event()
        self.release_first = threading.Event()

    def __enter__(self) -> "_GateLock":
        self._acquire()
        return self

    def __exit__(self, *_args: object) -> None:
        self._release()

    def _acquire(self) -> None:
        with self._cv:
            self.waiters += 1
            self._cv.notify_all()
            while self._held:
                self._cv.wait()
            self.waiters -= 1
            self._held = True
            first = self._hold_first
            self._hold_first = False
        if first:
            self.entered.set()
            self.release_first.wait()

    def _release(self) -> None:
        with self._cv:
            self._held = False
            self._cv.notify()

    def wait_for_waiter(self) -> None:
        with self._cv:
            while self.waiters < 1:
                self._cv.wait()


def _chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id="wordpress:page:1:chunk:0",
        document_id="wordpress:page:1",
        source="wordpress",
        source_id="1",
        title="Lifecycle",
        url="https://example.test/lifecycle",
        content_type="page",
        text="Lifecycle keyword retrieval.",
        heading_path=["Lifecycle"],
        sequence=0,
    )


def _prepare(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    **overrides: Any,
) -> None:
    corpus_path = tmp_path / "chunks.json"
    corpus_path.write_text(
        json.dumps([_chunk().model_dump(mode="json")]),
        encoding="utf-8",
    )
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
        "qdrant_timeout_seconds": 7,
        "reranking_provider": "voyage",
        "reranking_model": "rerank-2.5",
        "voyage_timeout_seconds": 11.5,
        "voyage_max_retries": 2,
        "lexical_corpus_path": corpus_path,
        "generation_enabled": True,
        "generation_model": "gpt-5.6-terra",
        "generation_context_budget_tokens": 8_000,
        "generation_max_output_tokens": 1_000,
        "openai_timeout_seconds": 44.0,
        "openai_max_retries": 1,
        "retrieval_vector_candidate_depth": 20,
        "retrieval_lexical_candidate_depth": 20,
        "retrieval_fused_candidate_depth": 20,
        "retrieval_rrf_k": 60,
        "retrieval_support_cutoff": 0.70,
    }
    values.update(overrides)
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)


def _sdk_client() -> MagicMock:
    client = MagicMock()
    client.embed.return_value = SimpleNamespace(embeddings=[[0.1, 0.2]])
    client.rerank.return_value = SimpleNamespace(results=[])
    client.query_points.return_value = SimpleNamespace(points=[])
    return client


def test_concurrent_first_retrieve_builds_each_dependency_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    _prepare(monkeypatch, tmp_path)
    voyage_clients: list[MagicMock] = []
    qdrant_clients: list[MagicMock] = []
    bm25_builds = 0
    real_init = Bm25Retriever.__init__

    def counting_init(self: Bm25Retriever, chunks: list[DocumentChunk]) -> None:
        nonlocal bm25_builds
        bm25_builds += 1
        real_init(self, chunks)

    def voyage_factory(*_args: object, **kwargs: object) -> MagicMock:
        assert kwargs["timeout"] == 11.5
        assert kwargs["max_retries"] == 2
        client = _sdk_client()
        voyage_clients.append(client)
        return client

    def qdrant_factory(*_args: object, **kwargs: object) -> MagicMock:
        assert kwargs["timeout"] == 7
        client = _sdk_client()
        qdrant_clients.append(client)
        return client

    monkeypatch.setattr(Bm25Retriever, "__init__", counting_init)
    gate = _GateLock()
    lazy = get_retrieval_service()
    lazy._lock = gate  # type: ignore[attr-defined]
    errors: list[BaseException] = []

    def retrieve() -> None:
        try:
            lazy.retrieve(RetrievalRequest(query="keyword", limit=5))
        except BaseException as exc:
            errors.append(exc)

    with (
        patch("voyageai.client.Client", side_effect=voyage_factory),
        patch(
            "rag_service.vectorstores.qdrant.QdrantClient",
            side_effect=qdrant_factory,
        ),
    ):
        first = threading.Thread(target=retrieve)
        first.start()
        assert gate.entered.wait(timeout=2)
        second = threading.Thread(target=retrieve)
        second.start()
        gate.wait_for_waiter()
        assert voyage_clients == []
        assert qdrant_clients == []
        assert bm25_builds == 0
        gate.release_first.set()
        first.join(timeout=2)
        second.join(timeout=2)
        lazy.retrieve(RetrievalRequest(query="keyword", limit=5))

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert len(voyage_clients) == 2
    assert len(qdrant_clients) == 1
    assert bm25_builds == 1
    for client in voyage_clients:
        client.close.assert_not_called()

    service = lazy._service  # type: ignore[attr-defined]
    barrier = threading.Barrier(2)
    overlapped: list[int] = []

    def overlapping(_request: RetrievalRequest) -> list[object]:
        barrier.wait(timeout=2)
        overlapped.append(1)
        return []

    service.retrieve = overlapping

    def retrieve_again() -> None:
        lazy.retrieve(RetrievalRequest(query="keyword", limit=5))

    again = [threading.Thread(target=retrieve_again) for _ in range(2)]
    for thread in again:
        thread.start()
    for thread in again:
        thread.join(timeout=2)
    assert not any(thread.is_alive() for thread in again)
    assert overlapped == [1, 1]
    assert bm25_builds == 1


def test_concurrent_first_answer_builds_one_openai_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    _prepare(monkeypatch, tmp_path)
    openai_calls: list[dict[str, object]] = []
    gate = _GateLock()

    def openai_factory(**kwargs: object) -> MagicMock:
        openai_calls.append(kwargs)
        return MagicMock()

    real_create = __import__(
        "rag_service.generation.factory",
        fromlist=["create_answer_generator"],
    ).create_answer_generator

    def wrapped(current: object) -> object:
        generator = real_create(current)
        generator._language_model._client_lock = gate
        return generator

    monkeypatch.setattr(
        "rag_service.api.dependencies.create_answer_generator",
        wrapped,
    )
    lazy = get_answer_generator()
    errors: list[BaseException] = []

    def generate() -> None:
        try:
            lazy.generate(question="What is lifecycle?", results=[])
        except BaseException as exc:
            errors.append(exc)

    with patch(
        "rag_service.generation.providers.openai.OpenAI",
        side_effect=openai_factory,
    ):
        first = threading.Thread(target=generate)
        first.start()
        assert gate.entered.wait(timeout=2)
        second = threading.Thread(target=generate)
        second.start()
        gate.wait_for_waiter()
        assert openai_calls == []
        gate.release_first.set()
        first.join(timeout=2)
        second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert all("closed" not in str(exc) for exc in errors)
    assert len(openai_calls) == 1
    assert openai_calls[0]["timeout"] == 44.0
    assert openai_calls[0]["max_retries"] == 1
    assert openai_calls[0]["api_key"] == "openai-test-key"

    generator = lazy._generator  # type: ignore[attr-defined]
    barrier = threading.Barrier(2)
    overlapped: list[int] = []

    def overlapping(**_kwargs: object) -> object:
        barrier.wait(timeout=2)
        overlapped.append(1)
        return object()

    generator.generate = overlapping

    def generate_again() -> None:
        lazy.generate(question="What is lifecycle?", results=[])

    again = [threading.Thread(target=generate_again) for _ in range(2)]
    for thread in again:
        thread.start()
    for thread in again:
        thread.join(timeout=2)
    assert not any(thread.is_alive() for thread in again)
    assert overlapped == [1, 1]
    assert len(openai_calls) == 1


def test_validation_and_authentication_do_not_construct_providers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    api_key_headers: dict[str, str],
) -> None:
    _prepare(monkeypatch, tmp_path)
    with (
        patch("voyageai.client.Client") as voyage,
        patch("rag_service.vectorstores.qdrant.QdrantClient") as qdrant,
        patch("rag_service.generation.providers.openai.OpenAI") as openai,
        TestClient(app) as client,
    ):
        unauthorized = client.post("/v1/search", json={"query": "keyword"})
        invalid = client.post(
            "/v1/search",
            json={"limit": 0},
            headers=api_key_headers,
        )

    assert unauthorized.status_code == 401
    assert invalid.status_code == 422
    voyage.assert_not_called()
    qdrant.assert_not_called()
    openai.assert_not_called()


def test_search_only_does_not_construct_openai(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    api_key_headers: dict[str, str],
) -> None:
    _prepare(
        monkeypatch,
        tmp_path,
        generation_enabled=False,
        openai_api_key=None,
    )
    with (
        patch("voyageai.client.Client", side_effect=lambda **_kwargs: _sdk_client()),
        patch(
            "rag_service.vectorstores.qdrant.QdrantClient",
            side_effect=lambda **_kwargs: _sdk_client(),
        ),
        patch("rag_service.generation.providers.openai.OpenAI") as openai,
        TestClient(app) as client,
    ):
        search = client.post(
            "/v1/search",
            json={"query": "keyword"},
            headers=api_key_headers,
        )
        answer = client.post(
            "/v1/answer",
            json={"query": "keyword"},
            headers=api_key_headers,
        )

    assert search.status_code == 200
    assert answer.status_code == 503
    assert answer.json()["error"]["code"] == "answer_unavailable"
    openai.assert_not_called()


def test_shutdown_closes_owned_clients_and_restart_builds_new_ones(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    api_key_headers: dict[str, str],
) -> None:
    _prepare(monkeypatch, tmp_path)
    qdrant_clients: list[MagicMock] = []

    def qdrant_factory(**_kwargs: object) -> MagicMock:
        client = _sdk_client()
        qdrant_clients.append(client)
        return client

    with (
        patch("voyageai.client.Client", side_effect=lambda **_kwargs: _sdk_client()),
        patch(
            "rag_service.vectorstores.qdrant.QdrantClient",
            side_effect=qdrant_factory,
        ),
    ):
        with TestClient(app) as client:
            first = client.post(
                "/v1/search",
                json={"query": "keyword"},
                headers=api_key_headers,
            )
            client.post(
                "/v1/search",
                json={"query": "keyword"},
                headers=api_key_headers,
            )
        assert first.status_code == 200
        assert len(qdrant_clients) == 1
        qdrant_clients[0].close.assert_called_once()
        first_searches = qdrant_clients[0].query_points.call_count

        with TestClient(app) as client:
            second = client.post(
                "/v1/search",
                json={"query": "keyword"},
                headers=api_key_headers,
            )

    assert second.status_code == 200
    assert len(qdrant_clients) == 2
    assert qdrant_clients[0].query_points.call_count == first_searches
    assert qdrant_clients[1].query_points.call_count == 1
    qdrant_clients[1].close.assert_called_once()
