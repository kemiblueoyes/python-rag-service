import pytest
from pydantic import SecretStr

from rag_service.config import settings

TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def configure_api_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr(TEST_API_KEY),
    )


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    return {
        "X-API-Key": TEST_API_KEY,
    }