from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from rag_service.api.models import (
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
)
from rag_service.retrieval import RetrievalUnavailableError


class AnswerUnavailableError(RuntimeError):
    """Raised when a grounded answer cannot be produced."""

async def request_validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return request validation failures using the public API error format."""

    details: list[ErrorDetail] = []

    for error in exc.errors():
        location = [
            str(part)
            for part in error["loc"]
            if part != "body"
        ]

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