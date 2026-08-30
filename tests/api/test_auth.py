import pytest
from pydantic import SecretStr

from rag_service.api.auth import (
    APIAuthenticationConfigurationError,
    InvalidAPIKeyError,
    require_api_key,
)
from rag_service.config import settings


def test_require_api_key_accepts_matching_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr("test-api-key"),
    )

    require_api_key("test-api-key")


def test_require_api_key_rejects_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr("test-api-key"),
    )

    with pytest.raises(InvalidAPIKeyError):
        require_api_key(None)


def test_require_api_key_rejects_incorrect_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr("test-api-key"),
    )

    with pytest.raises(InvalidAPIKeyError):
        require_api_key("wrong-api-key")


def test_require_api_key_rejects_missing_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        None,
    )

    with pytest.raises(APIAuthenticationConfigurationError):
        require_api_key("test-api-key")