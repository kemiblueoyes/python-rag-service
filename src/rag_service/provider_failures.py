"""Classify documented provider failures by exception type or status code.

Temporary failures are connection errors, timeouts, rate limits, and
provider server errors. Authentication and other documented client status
codes are configuration problems. Unrecognized exceptions are left alone
so programming errors are not reported as temporarily unavailable.
"""

import httpx
from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
)
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)
from voyageai.error import (
    APIConnectionError as VoyageConnectionError,
)
from voyageai.error import (
    APIError as VoyageAPIError,
)
from voyageai.error import (
    AuthenticationError as VoyageAuthenticationError,
)
from voyageai.error import (
    InvalidRequestError as VoyageInvalidRequestError,
)
from voyageai.error import (
    MalformedRequestError as VoyageMalformedRequestError,
)
from voyageai.error import (
    RateLimitError as VoyageRateLimitError,
)
from voyageai.error import (
    ServerError as VoyageServerError,
)
from voyageai.error import (
    ServiceUnavailableError as VoyageServiceUnavailableError,
)
from voyageai.error import (
    Timeout as VoyageTimeout,
)
from voyageai.error import (
    TryAgain as VoyageTryAgain,
)

from rag_service.errors import ServiceConfigurationError
from rag_service.generation.errors import (
    LanguageModelProviderError,
    LanguageModelResponseError,
)
from rag_service.retrieval.errors import RetrievalUnavailableError

_TEMPORARY_RETRIEVAL_ERRORS = (
    VoyageConnectionError,
    VoyageTimeout,
    VoyageRateLimitError,
    VoyageServerError,
    VoyageServiceUnavailableError,
    VoyageTryAgain,
    ResponseHandlingException,
    httpx.TransportError,
)
_CONFIGURATION_RETRIEVAL_ERRORS = (
    VoyageAuthenticationError,
    VoyageInvalidRequestError,
    VoyageMalformedRequestError,
)
_TEMPORARY_STATUS = frozenset({408, 429})
_CONFIGURATION_STATUS = frozenset({400, 401, 403, 404, 422})

def _retrieval_configuration() -> ServiceConfigurationError:
    return ServiceConfigurationError(
        operation="retrieval",
        reason="provider_configuration_rejected",
        diagnostic=(
            "The retrieval provider rejected the configured model, "
            "collection, or credentials. Check VOYAGE_API_KEY, "
            "EMBEDDING_MODEL, RERANKING_MODEL, QDRANT_URL, "
            "QDRANT_COLLECTION, and QDRANT_API_KEY."
        ),
    )


def _generation_configuration() -> ServiceConfigurationError:
    return ServiceConfigurationError(
        operation="generation",
        reason="provider_configuration_rejected",
        diagnostic=(
            "The language-model provider rejected the configured model or "
            "credentials. Check OPENAI_API_KEY and GENERATION_MODEL."
        ),
    )


def retrieval_exception_for(exc: BaseException) -> Exception | None:
    """Return a safe retrieval exception, or None to propagate exc."""

    if isinstance(exc, _TEMPORARY_RETRIEVAL_ERRORS):
        return RetrievalUnavailableError("Retrieval could not be completed.")
    if isinstance(exc, _CONFIGURATION_RETRIEVAL_ERRORS):
        return _retrieval_configuration()
    if isinstance(exc, VoyageAPIError):
        return _retrieval_for_status(_status_code(exc))
    if isinstance(exc, UnexpectedResponse):
        return _retrieval_for_status(exc.status_code)
    if isinstance(exc, httpx.HTTPStatusError):
        return _retrieval_for_status(exc.response.status_code)
    return None


def language_model_exception_for(exc: BaseException) -> Exception | None:
    """Return a safe language-model exception, or None to propagate exc."""

    if isinstance(exc, APIConnectionError):
        return LanguageModelProviderError(
            "OpenAI answer-generation request failed"
        )
    if isinstance(exc, APIResponseValidationError):
        return LanguageModelResponseError(
            "OpenAI returned an invalid structured answer"
        )
    if isinstance(exc, APIStatusError):
        return _generation_for_status(exc.status_code)
    return None


def _retrieval_for_status(status: int | None) -> Exception | None:
    if status is None:
        return None
    if status in _TEMPORARY_STATUS or status >= 500:
        return RetrievalUnavailableError("Retrieval could not be completed.")
    if status in _CONFIGURATION_STATUS:
        return _retrieval_configuration()
    return None


def _generation_for_status(status: int) -> Exception | None:
    if status in _TEMPORARY_STATUS or status >= 500:
        return LanguageModelProviderError(
            "OpenAI answer-generation request failed"
        )
    if status in _CONFIGURATION_STATUS:
        return _generation_configuration()
    return None


def _status_code(exc: VoyageAPIError) -> int | None:
    status = exc.http_status
    if isinstance(status, int):
        return status
    return None
