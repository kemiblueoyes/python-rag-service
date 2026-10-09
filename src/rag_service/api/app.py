# Used to confirm that the Python service starts and responds correctly
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.types import ExceptionHandler

from rag_service.api.auth import (
    APIAuthenticationConfigurationError,
    InvalidAPIKeyError,
)
from rag_service.api.dependencies import shutdown_api_dependencies
from rag_service.api.errors import (
    AnswerUnavailableError,
    UnexpectedErrorMiddleware,
    answer_unavailable_exception_handler,
    authentication_configuration_exception_handler,
    configuration_exception_handler,
    invalid_api_key_exception_handler,
    missing_language_model_key_exception_handler,
    request_validation_exception_handler,
    retrieval_unavailable_exception_handler,
)
from rag_service.api.models import HealthResponse
from rag_service.api.routes.answer import router as answer_router
from rag_service.api.routes.search import router as search_router
from rag_service.api.startup import validate_api_configuration
from rag_service.config import settings
from rag_service.errors import ServiceConfigurationError
from rag_service.generation.errors import MissingLanguageModelAPIKeyError
from rag_service.logging_config import configure_logging
from rag_service.retrieval import RetrievalUnavailableError


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure logging, then validate local API configuration."""
    configure_logging(settings.log_level)
    validate_api_configuration(settings)
    try:
        yield
    finally:
        shutdown_api_dependencies()


app = FastAPI(
    title="Python RAG Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_exception_handler(
    RequestValidationError,
    cast(ExceptionHandler, request_validation_exception_handler),
)

app.add_exception_handler(
    RetrievalUnavailableError,
    cast(ExceptionHandler, retrieval_unavailable_exception_handler),
)

app.include_router(search_router)
app.include_router(answer_router)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health",
    description=(
        "Check whether the Python RAG Service is running and responding to requests."
    ),
)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


app.add_exception_handler(
    AnswerUnavailableError,
    cast(ExceptionHandler, answer_unavailable_exception_handler),
)

app.add_exception_handler(
    InvalidAPIKeyError,
    cast(ExceptionHandler, invalid_api_key_exception_handler),
)

app.add_exception_handler(
    APIAuthenticationConfigurationError,
    cast(
        ExceptionHandler,
        authentication_configuration_exception_handler,
    ),
)

app.add_exception_handler(
    MissingLanguageModelAPIKeyError,
    cast(ExceptionHandler, missing_language_model_key_exception_handler),
)

app.add_exception_handler(
    ServiceConfigurationError,
    cast(ExceptionHandler, configuration_exception_handler),
)

# FastAPI sends an Exception handler to ServerErrorMiddleware, which
# re-raises after the response. Uvicorn would then print the original
# exception. This middleware returns the safe response and stops there.
app.add_middleware(UnexpectedErrorMiddleware)
