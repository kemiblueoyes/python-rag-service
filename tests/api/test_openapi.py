from fastapi.testclient import TestClient

from rag_service.api.app import app


def test_openapi_defines_api_key_security_scheme() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()
    security_schemes = schema["components"]["securitySchemes"]

    assert "APIKeyHeader" in security_schemes
    assert security_schemes["APIKeyHeader"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }


def test_search_requires_api_key_in_openapi() -> None:
    schema = app.openapi()

    operation = schema["paths"]["/v1/search"]["post"]

    assert {"APIKeyHeader": []} in operation["security"]


def test_answer_requires_api_key_in_openapi() -> None:
    schema = app.openapi()

    operation = schema["paths"]["/v1/answer"]["post"]

    assert {"APIKeyHeader": []} in operation["security"]


def test_health_does_not_require_api_key_in_openapi() -> None:
    schema = app.openapi()

    operation = schema["paths"]["/health"]["get"]

    assert "security" not in operation