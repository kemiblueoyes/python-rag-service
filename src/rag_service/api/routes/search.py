from typing import Annotated

from fastapi import APIRouter, Depends

from rag_service.api.dependencies import get_retrieval_service
from rag_service.api.models import (
    ErrorResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from rag_service.retrieval import RetrievalRequest, RetrievalService

router = APIRouter(
    prefix="/v1",
    tags=["Search"],
)


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search indexed documentation",
    description=(
        "Retrieve documentation chunks ranked by semantic similarity "
        "without generating an answer."
    ),
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Request validation failed.",
        },
        503: {
            "model": ErrorResponse,
            "description": "Search is temporarily unavailable.",
        },
    },
)
def search(
    request: SearchRequest,
    retrieval_service: Annotated[
        RetrievalService,
        Depends(get_retrieval_service),
    ],
) -> SearchResponse:
    filters = (
        request.filters.model_dump(exclude_none=True)
        if request.filters is not None
        else {}
    )

    retrieval_results = retrieval_service.retrieve(
        RetrievalRequest(
            query=request.query,
            limit=request.limit,
            filters=filters,
        )
    )

    return SearchResponse(
        query=request.query,
        results=[
            SearchResult(
                chunk_id=result.chunk.chunk_id,
                document_id=result.chunk.document_id,
                title=result.chunk.title,
                heading_path=result.chunk.heading_path,
                anchor=result.chunk.anchor,
                excerpt=result.chunk.text,
                url=result.chunk.url,
                score=result.score,
            )
            for result in retrieval_results
        ],
    )