from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from rag_service.api.app import app
from rag_service.config import settings
from tests.api.test_lifecycle import _prepare


@pytest.mark.parametrize(
    "path",
    [
        "/v1/search",
        "/v1/answer",
    ],
)
def test_public_api_rejects_missing_api_key(
    path: str,
) -> None:
    client = TestClient(app)

    response = client.post(
        path,
        json={"query": "What is RAG?"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "authentication_failed",
            "message": "A valid API key is required.",
            "details": [],
        }
    }


@pytest.mark.parametrize(
    "path",
    ["/v1/search", "/v1/answer"],
)
@pytest.mark.parametrize(
    "supplied_key",
    [
        "short-key",
        "wrong-api-ky",
        "test-api-key-extra",
    ],
)
def test_public_api_rejects_incorrect_api_key_without_provider_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    path: str,
    supplied_key: str,
) -> None:
    _prepare(monkeypatch, tmp_path)
    with (
        patch("voyageai.client.Client") as voyage,
        patch("rag_service.vectorstores.qdrant.QdrantClient") as qdrant,
        patch("rag_service.generation.providers.openai.OpenAI") as openai,
        TestClient(app) as client,
    ):
        response = client.post(
            path,
            json={"query": "What is RAG?"},
            headers={"X-API-Key": supplied_key},
        )

    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "authentication_failed",
        "message": "A valid API key is required.",
        "details": [],
    }
    voyage.assert_not_called()
    qdrant.assert_not_called()
    openai.assert_not_called()


@pytest.mark.parametrize(
    "configured_key",
    [None, SecretStr("")],
)
def test_search_returns_503_when_authentication_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
    configured_key: SecretStr | None,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        configured_key,
    )

    client = TestClient(app)

    response = client.post(
        "/v1/search",
        json={"query": "What is RAG?"},
        headers={"X-API-Key": "some-key"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "authentication_unavailable"


def test_health_check_does_not_require_api_key() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}