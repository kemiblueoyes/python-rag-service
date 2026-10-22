import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from rag_service.api import dependencies
from rag_service.api.app import app
from rag_service.config import settings
from rag_service.generation import GeneratedAnswer
from rag_service.generation.models import ContextSource
from rag_service.lexical import refreshing
from rag_service.models.chunk import DocumentChunk
from rag_service.vectorstores.base import SearchResult


def publish(path: Path, text: str) -> None:
    chunk = DocumentChunk(
        chunk_id=text,
        document_id="wordpress:page:1",
        source="wordpress",
        source_id="1",
        title="Retrieval",
        url="https://example.test/page",
        content_type="page",
        text=text,
        heading_path=[],
        sequence=0,
    )
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps([chunk.model_dump(mode="json")]))
    temporary.replace(path)


@pytest.fixture
def running_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "chunks.json"
    publish(path, "original retrieval")
    monkeypatch.setattr(settings, "lexical_corpus_path", path)
    monkeypatch.setattr(settings, "generation_enabled", True)
    monkeypatch.setattr(settings, "voyage_api_key", "test")
    monkeypatch.setattr(settings, "openai_api_key", "test")
    embedding = MagicMock()
    vector = MagicMock()
    vector.search.return_value = []
    reranker = MagicMock()
    reranker.rerank.side_effect = lambda query, results, limit: [
        SearchResult(chunk=result.chunk, score=1.0) for result in results[:limit]
    ]
    for name, resource in [
        ("create_embedding_provider", embedding),
        ("create_vector_store", vector),
        ("create_reranker", reranker),
    ]:
        monkeypatch.setattr(
            f"rag_service.retrieval.factory.{name}", lambda _, r=resource: r
        )
    generator = MagicMock()
    generator.generate.side_effect = lambda question, results: GeneratedAnswer(
        answer=results[0].chunk.text,
        sources=(ContextSource(citation_id="S1", chunk=results[0].chunk, score=1.0),),
        sufficient_evidence=True,
    )
    dependencies.shutdown_api_dependencies()
    app.dependency_overrides[dependencies.get_answer_generator] = lambda: generator
    try:
        with TestClient(app) as client:
            yield client, path, (embedding, vector, reranker)
    finally:
        app.dependency_overrides.clear()
        dependencies.shutdown_api_dependencies()


@pytest.mark.parametrize("endpoint", ["search", "answer"])
def test_running_api_refresh_and_recovery(
    running_api, api_key_headers, monkeypatch, endpoint
):
    client, path, resources = running_api
    builder = MagicMock(wraps=refreshing.create_lexical_retriever)
    monkeypatch.setattr(refreshing, "create_lexical_retriever", builder)

    def request():
        return client.post(
            f"/v1/{endpoint}", json={"query": "retrieval"}, headers=api_key_headers
        )

    assert "original retrieval" in request().text
    assert "original retrieval" in request().text
    assert builder.call_count == 1
    service = dependencies.get_retrieval_service()
    publish(path, "updated retrieval")
    response = request()
    assert response.status_code == 200
    assert "updated retrieval" in response.text
    assert "original retrieval" not in response.text
    assert dependencies.get_retrieval_service() is service
    assert builder.call_count == 2
    path.write_text("invalid json")
    for _ in range(2):
        failure = request()
        assert failure.status_code == 500
        assert failure.json()["error"]["code"] == "configuration_error"
        assert "updated retrieval" not in failure.text
    publish(path, "recovered retrieval")
    assert "recovered retrieval" in request().text
    for resource in resources:
        resource.close.assert_not_called()


def test_concurrent_refresh_publishes_one_complete_index(
    running_api, api_key_headers, monkeypatch
):
    client, path, resources = running_api

    def request():
        return client.post(
            "/v1/search", json={"query": "retrieval"}, headers=api_key_headers
        )

    assert request().status_code == 200
    publish(path, "concurrent retrieval")
    entered, release = Event(), Event()
    original = refreshing.create_lexical_retriever

    def build(settings):
        entered.set()
        assert release.wait(10)
        return original(settings)

    builder = MagicMock(side_effect=build)
    monkeypatch.setattr(refreshing, "create_lexical_retriever", builder)
    with ThreadPoolExecutor(max_workers=6) as pool:
        first = pool.submit(request)
        assert entered.wait(10)
        others = [pool.submit(request) for _ in range(5)]
        assert not first.done()
        release.set()
        responses = [future.result(timeout=20) for future in [first, *others]]
    assert builder.call_count == 1
    assert all(response.status_code == 200 for response in responses)
    assert all("concurrent retrieval" in response.text for response in responses)
    for resource in resources:
        resource.close.assert_not_called()
