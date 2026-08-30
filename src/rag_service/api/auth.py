from secrets import compare_digest
from typing import Annotated

from fastapi import Security
from fastapi.security import APIKeyHeader

from rag_service.config import settings

API_KEY_HEADER_NAME = "X-API-Key"

api_key_header = APIKeyHeader(
    name=API_KEY_HEADER_NAME,
    auto_error=False,
)


class InvalidAPIKeyError(RuntimeError):
    """Raised when a request does not provide a valid API key."""


class APIAuthenticationConfigurationError(RuntimeError):
    """Raised when API authentication is not configured."""


def require_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
) -> None:
    configured_key = (
        settings.rag_api_key.get_secret_value()
        if settings.rag_api_key is not None
        else ""
    )

    if not configured_key:
        raise APIAuthenticationConfigurationError(
            "RAG_API_KEY is not configured."
        )

    if api_key is None or not compare_digest(
        api_key.encode("utf-8"),
        configured_key.encode("utf-8"),
    ):
        raise InvalidAPIKeyError(
            "A valid API key is required."
        )