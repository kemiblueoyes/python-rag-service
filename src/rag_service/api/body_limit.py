"""Reject oversized search and answer bodies before JSON parsing."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from rag_service.api.limits import (
    CAPABILITY_PATHS,
    REQUEST_BODY_MAX_BYTES,
    REQUEST_TOO_LARGE_CODE,
    REQUEST_TOO_LARGE_MESSAGE,
)
from rag_service.api.models import ErrorBody, ErrorResponse


def request_too_large_response() -> JSONResponse:
    """Return the public 413 body without echoing the request."""

    payload = ErrorResponse(
        error=ErrorBody(
            code=REQUEST_TOO_LARGE_CODE,
            message=REQUEST_TOO_LARGE_MESSAGE,
        )
    )
    return JSONResponse(
        status_code=413,
        content=payload.model_dump(mode="json"),
    )


class RequestBodyLimitMiddleware:
    """Count received bytes for the capability endpoints.

    ``Content-Length`` is not the limit. A missing header, a header that
    doesn't match the body, and a body split across chunks all use the
    same byte count. The middleware keeps at most the allowed number of
    bytes, then replays that body to the application.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int = REQUEST_BODY_MAX_BYTES,
        paths: frozenset[str] = CAPABILITY_PATHS,
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.paths = paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        if scope.get("path") not in self.paths:
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body = message.get("body", b"")
            size = len(body)
            if total + size > self.max_bytes:
                response = request_too_large_response()
                await response(scope, receive, send)
                return
            if size:
                chunks.append(bytes(body))
            total += size
            if not message.get("more_body", False):
                break

        payload = b"".join(chunks)
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {
                    "type": "http.request",
                    "body": payload,
                    "more_body": False,
                }
            return await receive()

        await self.app(scope, replay, send)
