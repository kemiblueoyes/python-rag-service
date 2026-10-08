import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from rag_service.api.auth import (
    APIAuthenticationConfigurationError,
    InvalidAPIKeyError,
)
from rag_service.api.models import (
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
)
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
    logger.error(
        "operation=%s reason=%s: %s",
        operation,
        reason,
        message,
        extra={"operation": operation, "reason": reason},
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
