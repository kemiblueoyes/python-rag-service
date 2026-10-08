import logging
from concurrent.futures import CancelledError as FutureCancelledError

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from rag_service.api.auth import (
    APIAuthenticationConfigurationError,
    InvalidAPIKeyError,
)
from rag_service.api.models import (
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
)
from rag_service.errors import ServiceConfigurationError
from rag_service.generation.errors import (
    CitationValidationError,
    ContextBudgetError,
    GenerationDisabledError,
    LanguageModelError,
    LanguageModelProviderError,
    LanguageModelRefusalError,
    LanguageModelResponseError,
    MissingLanguageModelAPIKeyError,
)
from rag_service.retrieval import RetrievalUnavailableError

CONFIGURATION_ERROR_MESSAGE = "The service configuration is invalid."
INTERNAL_ERROR_MESSAGE = "The service couldn't complete the request."

logger = logging.getLogger(__name__)

# Only application-owned constants reach the log. Never stringify exceptions,
# attach exc_info, or include request data: provider causes can contain secrets.
# Specific subclasses must precede their parent classes.
_FAILURE_DIAGNOSTICS = (
    (
        GenerationDisabledError,
        "generation",
        "generation_disabled",
        "Answer generation is disabled. "
        "Set GENERATION_ENABLED to true and restart the service.",
    ),
    (
        MissingLanguageModelAPIKeyError,
        "generation",
        "missing_provider_api_key",
        "Configure the language-model provider API key and restart the service.",
    ),
    (
        LanguageModelRefusalError,
        "generation",
        "provider_refusal",
        "The language model refused the generation request.",
    ),
    (
        LanguageModelResponseError,
        "generation",
        "invalid_provider_response",
        "The language model returned no usable structured answer.",
    ),
    (
        LanguageModelProviderError,
        "generation",
        "provider_request_failed",
        "The language-model provider request failed.",
    ),
    (
        LanguageModelError,
        "generation",
        "language_model_failed",
        "The language-model operation failed.",
    ),
    (
        ContextBudgetError,
        "context_assembly",
        "context_budget_exceeded",
        "The highest-ranked source exceeds the context budget.",
    ),
    (
        CitationValidationError,
        "citation_validation",
        "invalid_citations",
        "The generated answer failed citation validation.",
    ),
    (
        RetrievalUnavailableError,
        "retrieval",
        "retrieval_dependency_failed",
        "The retrieval pipeline could not complete.",
    ),
    (
        APIAuthenticationConfigurationError,
        "authentication",
        "missing_service_api_key",
        "Configure RAG_API_KEY and restart the service.",
    ),
)


def _failure_diagnostic(exc: Exception) -> tuple[str, str, str]:
    """Classify application exceptions without inspecting their messages."""
    for error_type, operation, reason, message in _FAILURE_DIAGNOSTICS:
        if isinstance(exc, error_type):
            return operation, reason, message
    return (
        "answer",
        "unclassified_answer_failure",
        "The answer workflow could not complete.",
    )


def _log_service_failure(exc: Exception) -> None:
    """Log one safe diagnostic for a handled service failure."""
    operation, reason, message = _failure_diagnostic(exc)
    _log_diagnostic(operation, reason, message)


def _log_diagnostic(operation: str, reason: str, message: str) -> None:
    logger.error(
        "operation=%s reason=%s: %s",
        operation,
        reason,
        message,
        extra={"operation": operation, "reason": reason},
    )


def _error_json(status_code: int, code: str, message: str) -> JSONResponse:
    response = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


class AnswerUnavailableError(RuntimeError):
    """Raised when a grounded answer cannot be produced."""


async def request_validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return request validation failures using the public API error format."""

    details: list[ErrorDetail] = []

    for error in exc.errors():
        location = [str(part) for part in error["loc"] if part != "body"]

        details.append(
            ErrorDetail(
                field=".".join(location) or None,
                message=str(error["msg"]),
            )
        )

    response = ErrorResponse(
        error=ErrorBody(
            code="validation_error",
            message="Request validation failed.",
            details=details,
        )
    )

    return JSONResponse(
        status_code=422,
        content=response.model_dump(mode="json"),
    )


async def retrieval_unavailable_exception_handler(
    _request: Request,
    _exc: RetrievalUnavailableError,
) -> JSONResponse:
    """Return retrieval dependency failures using the public API error format."""

    _log_service_failure(_exc)

    response = ErrorResponse(
        error=ErrorBody(
            code="retrieval_unavailable",
            message="Search is temporarily unavailable.",
        )
    )

    return JSONResponse(
        status_code=503,
        content=response.model_dump(mode="json"),
    )


async def answer_unavailable_exception_handler(
    _request: Request,
    _exc: AnswerUnavailableError,
) -> JSONResponse:
    """Return answer-generation failures using the public API error format."""

    # The answer route wraps known application errors as the direct cause.
    # Do not traverse or serialize the underlying provider exception chain.
    cause = _exc.__cause__
    _log_service_failure(cause if isinstance(cause, Exception) else _exc)

    response = ErrorResponse(
        error=ErrorBody(
            code="answer_unavailable",
            message="Answer generation is temporarily unavailable.",
        )
    )

    return JSONResponse(
        status_code=503,
        content=response.model_dump(mode="json"),
    )


async def invalid_api_key_exception_handler(
    _request: Request,
    _exc: InvalidAPIKeyError,
) -> JSONResponse:
    """Return authentication failures using the public API error format."""

    response = ErrorResponse(
        error=ErrorBody(
            code="authentication_failed",
            message="A valid API key is required.",
        )
    )

    return JSONResponse(
        status_code=401,
        content=response.model_dump(mode="json"),
    )


async def authentication_configuration_exception_handler(
    _request: Request,
    _exc: APIAuthenticationConfigurationError,
) -> JSONResponse:
    """Return server-side authentication configuration failures."""

    _log_service_failure(_exc)

    response = ErrorResponse(
        error=ErrorBody(
            code="authentication_unavailable",
            message="API authentication is temporarily unavailable.",
        )
    )

    return JSONResponse(
        status_code=503,
        content=response.model_dump(mode="json"),
    )


async def missing_language_model_key_exception_handler(
    _request: Request,
    exc: MissingLanguageModelAPIKeyError,
) -> JSONResponse:
    """Return a fixed configuration error when the provider key is missing."""

    _log_service_failure(exc)
    return _error_json(500, "configuration_error", CONFIGURATION_ERROR_MESSAGE)


async def configuration_exception_handler(
    _request: Request,
    exc: ServiceConfigurationError,
) -> JSONResponse:
    """Return a fixed configuration error for a known settings problem."""

    _log_diagnostic(exc.operation, exc.reason, exc.diagnostic)
    return _error_json(500, "configuration_error", CONFIGURATION_ERROR_MESSAGE)


def _unexpected_error_response() -> JSONResponse:
    _log_diagnostic(
        "request",
        "unexpected_failure",
        "The service hit an unexpected error. Review the application code.",
    )
    return _error_json(500, "internal_error", INTERNAL_ERROR_MESSAGE)


class UnexpectedErrorMiddleware:
    """Convert unhandled request exceptions into a fixed JSON response.

    More specific handlers run first. This middleware does not re-raise, so
    the server does not log the original exception after the response.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            # asyncio.CancelledError is a BaseException and is not caught here.
            # concurrent.futures.CancelledError is an Exception on Python 3.14.
            if isinstance(exc, (BaseExceptionGroup, FutureCancelledError)):
                raise
            response = _unexpected_error_response()
            await response(scope, receive, send)
