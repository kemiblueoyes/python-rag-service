from typing import Annotated

from fastapi import APIRouter, Body, Depends

from rag_service.api.auth import require_api_key
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
    dependencies=[Depends(require_api_key)],
)

RESULTS_FOUND_REQUEST = {
    "query": "How does metadata improve retrieval?",
    "filters": {
        "content_type": "page",
    },
    "limit": 3,
}

RESULTS_FOUND_RESPONSE = {
    "query": "How does metadata improve retrieval?",
    "results": [
        {
            "chunk_id": "wordpress:page:1:chunk:0",
            "document_id": "wordpress:page:1",
            "title": "Metadata Strategy",
            "heading_path": ["Metadata filtering"],
            "anchor": "metadata-filtering",
            "excerpt": (
                "Metadata can narrow the documents considered "
                "during retrieval."
            ),
            "url": "https://example.test/metadata",
            "score": 0.91,
        }
    ],
}

NO_RESULTS_REQUEST = {
    "query": "What is the capital of Mars?",
}

NO_RESULTS_RESPONSE = {
    "query": "What is the capital of Mars?",
    "results": [],
}

SEARCH_REQUEST_EXAMPLES = {
    "results_found": {
        "summary": "Results found",
        "value": RESULTS_FOUND_REQUEST,
    },
    "no_results": {
        "summary": "No relevant results",
        "value": NO_RESULTS_REQUEST,
    },
}

SEARCH_RESPONSE_EXAMPLES = {
    "results_found": {
        "summary": "Results found",
        "value": RESULTS_FOUND_RESPONSE,
    },
    "no_results": {
        "summary": "No relevant results",
        "value": NO_RESULTS_RESPONSE,
    },
}

AUTHENTICATION_FAILED_RESPONSE = {
    "error": {
        "code": "authentication_failed",
        "message": "A valid API key is required.",
        "details": [],
    }
}

VALIDATION_ERROR_RESPONSE = {
    "error": {
        "code": "validation_error",
        "message": "Request validation failed.",
        "details": [
            {
                "field": "limit",
                "message": "Input should be greater than or equal to 1",
            }
        ],
    }
}

SEARCH_UNAVAILABLE_RESPONSE = {
    "error": {
        "code": "retrieval_unavailable",
        "message": "Search is temporarily unavailable.",
        "details": [],
    }
}

@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search indexed documentation",
    description=(
        "Retrieve documentation chunks through the hybrid retrieval pipeline "
        "without generating an answer."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "examples": SEARCH_RESPONSE_EXAMPLES,
                }
            },
        },
        401: {
            "model": ErrorResponse,
            "description": "Authentication failed.",
            "content": {
                "application/json": {
                    "examples": {
                        "authentication_failed": {
                            "summary": "Authentication failed",
                            "value": AUTHENTICATION_FAILED_RESPONSE,
                        }
                    }
                }
            },
        },
        422: {
            "model": ErrorResponse,
            "description": "Request validation failed.",
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "Validation error",
                            "value": VALIDATION_ERROR_RESPONSE,
                        }
                    }
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "Search is temporarily unavailable.",
            "content": {
                "application/json": {
                    "examples": {
                        "search_unavailable": {
                            "summary": "Search unavailable",
                            "value": SEARCH_UNAVAILABLE_RESPONSE,
                        }
                    }
                }
            },
        },
    },
)
def search(
    request: Annotated[
        SearchRequest,
        Body(openapi_examples=SEARCH_REQUEST_EXAMPLES),
    ],
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