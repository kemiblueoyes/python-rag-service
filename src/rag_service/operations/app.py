"""Run with one Uvicorn worker on port 8001, separate from the public API."""

import hashlib
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from secrets import compare_digest
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict

from rag_service.config import settings
from rag_service.operations.adapters import evaluate, index
from rag_service.operations.runner import (
    Adapter,
    JobConflict,
    Runner,
    RunnerUnavailable,
)

key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["index_wordpress", "evaluate_retrieval"]


def authenticate(key: Annotated[str | None, Security(key_header)]) -> None:
    configured = settings.operations_api_key
    if configured is None or not configured.get_secret_value():
        raise HTTPException(503, "Operations authentication is not configured.")
    if key is None or not compare_digest(
        hashlib.sha256(key.encode()).digest(),
        hashlib.sha256(configured.get_secret_value().encode()).digest(),
    ):
        raise HTTPException(401, "A valid operations API key is required.")


def create_app(
    database: Path = Path("data/operations/jobs.sqlite3"),
    adapters: Mapping[str, Adapter] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.runner = Runner(
            database,
            adapters
            if adapters is not None
            else {
                "index_wordpress": index,
                "evaluate_retrieval": evaluate,
            },
        )
        try:
            yield
        finally:
            app.state.runner.close()

    app = FastAPI(title="Local RAG operations", lifespan=lifespan)

    @app.exception_handler(RunnerUnavailable)
    async def unavailable(_request: Request, _exc: RunnerUnavailable) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "runner_unavailable",
                    "message": "The runner is unavailable.",
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # Do not echo arbitrary request inputs or headers in validation errors.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "Invalid job request or header.",
                }
            },
        )

    @app.get("/health")
    def health(request: Request) -> dict[str, str]:
        request.app.state.runner.health()
        return {"status": "ok"}

    @app.post("/jobs", dependencies=[Depends(authenticate)])
    def submit(
        submission: Submission,
        request: Request,
        response: Response,
        idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
    ) -> dict[str, Any]:
        if not idempotency_key.strip():
            raise HTTPException(422, "Idempotency-Key must not be blank.")
        try:
            job, created = request.app.state.runner.submit(
                submission.operation, idempotency_key
            )
        except JobConflict as exc:
            raise HTTPException(409, {"code": exc.code, "job_id": exc.job_id}) from None
        response.status_code = 202 if created else 200
        return dict(job)

    @app.get("/jobs/{job_id}", dependencies=[Depends(authenticate)])
    def get_job(job_id: str, request: Request) -> dict[str, Any]:
        job = request.app.state.runner.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found.")
        return dict(job)

    return app


app = create_app()
