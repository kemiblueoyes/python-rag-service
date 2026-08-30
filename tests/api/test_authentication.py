import pytest
from fastapi.testclient import TestClient

from rag_service.api.app import app
from rag_service.config import settings


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


def test_search_rejects_incorrect_api_key() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/search",
        json={"query": "What is RAG?"},
        headers={"X-API-Key": "wrong-api-key"},
    )

    assert response.status_code == 401


def test_search_returns_503_when_authentication_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        None,
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