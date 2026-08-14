# Used to confirm that the Python service starts and responds correctly
from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.types import ExceptionHandler

from rag_service.api.errors import (
    request_validation_exception_handler,
    retrieval_unavailable_exception_handler,
)
from rag_service.api.routes.search import router as search_router
from rag_service.retrieval import RetrievalUnavailableError

app = FastAPI(
    title="Python RAG Service",
    version="0.1.0",
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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
