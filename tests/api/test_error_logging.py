import logging
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from rag_service.api.app import app
from rag_service.api.dependencies import get_answer_generator, get_retrieval_service
from rag_service.api.errors import AnswerUnavailableError
from rag_service.config import settings
from rag_service.generation import AnswerGenerator
from rag_service.generation.errors import (
    CitationValidationError,
    ContextBudgetError,
    LanguageModelError,
    LanguageModelProviderError,
    LanguageModelRefusalError,
    LanguageModelResponseError,
)
from rag_service.generation.models import GenerationPrompt
from rag_service.generation.providers.openai import OpenAILanguageModel
from rag_service.retrieval import RetrievalService, RetrievalUnavailableError

SENSITIVE = "private-query sk-secret provider-body https://user:password@host"
LOGGER = "rag_service.api.errors"


@pytest.fixture(autouse=True)
def isolate_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app, "dependency_overrides", {})


def assert_safe_log(
    caplog: pytest.LogCaptureFixture, operation: str, reason: str
) -> None:
    records = [record for record in caplog.records if record.name == LOGGER]
    assert len(records) == 1
    record = records[0]
    assert record.levelno == logging.ERROR
    assert record.operation == operation  # type: ignore[attr-defined]
    assert record.reason == reason  # type: ignore[attr-defined]
    assert f"operation={operation} reason={reason}:" in record.getMessage()
    assert record.exc_info is None
    assert record.stack_info is None
    # Check structured fields and arguments too, not just the rendered message.
    assert SENSITIVE not in repr(record.__dict__)
    assert "test-api-key" not in repr(record.__dict__)


@pytest.mark.parametrize(
    ("failure", "operation", "reason"),
    [
        (
            LanguageModelProviderError(SENSITIVE),
            "generation",
            "provider_request_failed",
        ),
        (LanguageModelRefusalError(SENSITIVE), "generation", "provider_refusal"),
        (
            LanguageModelResponseError(SENSITIVE),
            "generation",
            "invalid_provider_response",
        ),
        (LanguageModelError(SENSITIVE), "generation", "language_model_failed"),
        (
            CitationValidationError(SENSITIVE),
            "citation_validation",
            "invalid_citations",
        ),
        (
            ContextBudgetError(budget_tokens=1, required_tokens=2),
            "context_assembly",
            "context_budget_exceeded",
        ),
        (
            RetrievalUnavailableError(SENSITIVE),
            "retrieval",
            "retrieval_dependency_failed",
        ),
        (AnswerUnavailableError(SENSITIVE), "answer", "unclassified_answer_failure"),
    ],
)
def test_answer_logs_safe_reason_and_preserves_response(
    failure: Exception,
    operation: str,
    reason: str,
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Even an SDK cause containing credentials must never be logged.
    failure.__cause__ = RuntimeError(SENSITIVE)
    retrieval = MagicMock(spec=RetrievalService)
    generator = MagicMock(spec=AnswerGenerator)
    retrieval.retrieve.return_value = []
    if isinstance(failure, RetrievalUnavailableError):
        retrieval.retrieve.side_effect = failure
    else:
        generator.generate.side_effect = failure
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    app.dependency_overrides[get_answer_generator] = lambda: generator

    with caplog.at_level(logging.ERROR, logger=LOGGER):
        response = TestClient(app).post(
            "/v1/answer", json={"query": SENSITIVE}, headers=api_key_headers
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "answer_unavailable",
            "message": "Answer generation is temporarily unavailable.",
            "details": [],
        }
    }
    assert_safe_log(caplog, operation, reason)


def test_search_logs_safe_retrieval_failure(
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = RetrievalUnavailableError(SENSITIVE)
    failure.__cause__ = RuntimeError(SENSITIVE)
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.side_effect = failure
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval

    response = TestClient(app).post(
        "/v1/search", json={"query": SENSITIVE}, headers=api_key_headers
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "retrieval_unavailable",
            "message": "Search is temporarily unavailable.",
            "details": [],
        }
    }
    assert_safe_log(caplog, "retrieval", "retrieval_dependency_failed")


def test_missing_provider_key_reaches_api_log(
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAILanguageModel(model="gpt-5.6-terra")
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.return_value = []
    generator = MagicMock(spec=AnswerGenerator)

    def generate(**_kwargs: object) -> None:
        provider.generate(
            GenerationPrompt(
                system_message=SENSITIVE,
                user_message=SENSITIVE,
            )
        )

    generator.generate.side_effect = generate
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    app.dependency_overrides[get_answer_generator] = lambda: generator
    response = TestClient(app).post(
        "/v1/answer", json={"query": SENSITIVE}, headers=api_key_headers
    )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "configuration_error",
            "message": "The service configuration is invalid.",
            "details": [],
        }
    }
    assert_safe_log(caplog, "generation", "missing_provider_api_key")


@pytest.mark.parametrize("path", ["/v1/search", "/v1/answer"])
def test_missing_service_key_logs_safe_configuration_failure(
    path: str,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "rag_api_key", None)
    response = TestClient(app).post(
        path, json={"query": SENSITIVE}, headers={"X-API-Key": SENSITIVE}
    )
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "authentication_unavailable",
            "message": "API authentication is temporarily unavailable.",
            "details": [],
        }
    }
    assert_safe_log(caplog, "authentication", "missing_service_api_key")


def test_successful_search_does_not_require_generation_key_or_log_failure(
    api_key_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(settings, "openai_api_key", None)
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.retrieve.return_value = []
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    response = TestClient(app).post(
        "/v1/search", json={"query": "What is RAG?"}, headers=api_key_headers
    )
    assert response.status_code == 200
    assert response.json() == {"query": "What is RAG?", "results": []}
    assert not [record for record in caplog.records if record.name == LOGGER]
