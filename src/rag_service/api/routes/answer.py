from typing import Annotated

from fastapi import APIRouter, Body, Depends

from rag_service.api.auth import require_api_key
from rag_service.api.dependencies import (
    get_answer_generator,
    get_retrieval_service,
)
from rag_service.api.errors import AnswerUnavailableError
from rag_service.api.models import (
    AnswerRequest,
    AnswerResponse,
    AnswerSource,
    ErrorResponse,
)
from rag_service.generation import AnswerGenerator
from rag_service.generation.errors import (
    CitationValidationError,
    ContextBudgetError,
    LanguageModelError,
)
from rag_service.retrieval import (
    RetrievalRequest,
    RetrievalService,
    RetrievalUnavailableError,
)

router = APIRouter(
    prefix="/v1",
    tags=["Answer"],
    dependencies=[Depends(require_api_key)],
)

ANSWER_RETRIEVAL_LIMIT = 5

GROUNDED_ANSWER_REQUEST = {
    "query": ("Why does inconsistent terminology cause retrieval failures?"),
    "filters": {
        "source": "wordpress",
    },
}

GROUNDED_ANSWER_RESPONSE = {
    "query": ("Why does inconsistent terminology cause retrieval failures?"),
    "answer": (
        "Inconsistent terminology can cause retrieval failures "
        "because the query and documentation may use different "
        "language for the same concept. [S1]"
    ),
    "sources": [
        {
            "citation_id": "S1",
            "chunk_id": "wordpress:page:1:chunk:0",
            "document_id": "wordpress:page:1",
            "title": "Retrieval Failures",
            "heading_path": ["Vocabulary mismatch"],
            "anchor": "vocabulary-mismatch",
            "excerpt": (
                "Inconsistent terminology can make relevant content harder to retrieve."
            ),
            "url": "https://example.test/retrieval-failures",
        }
    ],
    "sufficient_evidence": True,
}

INSUFFICIENT_EVIDENCE_REQUEST = {
    "query": "What is the capital of Mars?",
}

INSUFFICIENT_EVIDENCE_RESPONSE = {
    "query": "What is the capital of Mars?",
    "answer": (
        "The available documentation does not provide enough "
        "information to answer this question."
    ),
    "sources": [],
    "sufficient_evidence": False,
}

ANSWER_REQUEST_EXAMPLES = {
    "grounded_answer": {
        "summary": "Grounded answer",
        "value": GROUNDED_ANSWER_REQUEST,
    },
    "insufficient_evidence": {
        "summary": "Insufficient evidence",
        "value": INSUFFICIENT_EVIDENCE_REQUEST,
    },
}

ANSWER_RESPONSE_EXAMPLES = {
    "grounded_answer": {
        "summary": "Grounded answer",
        "value": GROUNDED_ANSWER_RESPONSE,
    },
    "insufficient_evidence": {
        "summary": "Insufficient evidence",
        "value": INSUFFICIENT_EVIDENCE_RESPONSE,
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
                "message": "Extra inputs are not permitted",
            }
        ],
    }
}

ANSWER_UNAVAILABLE_RESPONSE = {
    "error": {
        "code": "answer_unavailable",
        "message": "Answer generation is temporarily unavailable.",
        "details": [],
    }
}

@router.post(
    "/answer",
    response_model=AnswerResponse,
    summary="Generate a grounded answer",
    description=(
        "Retrieve relevant documentation and generate an answer "
        "grounded in validated source content."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "examples": ANSWER_RESPONSE_EXAMPLES,
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
            "description": "Answer generation is temporarily unavailable.",
            "content": {
                "application/json": {
                    "examples": {
                        "answer_unavailable": {
                            "summary": "Answer unavailable",
                            "value": ANSWER_UNAVAILABLE_RESPONSE,
                        }
                    }
                }
            },
        }
    }
)
def answer(
    request: Annotated[
        AnswerRequest,
        Body(openapi_examples=ANSWER_REQUEST_EXAMPLES),
    ],
    retrieval_service: Annotated[
        RetrievalService,
        Depends(get_retrieval_service),
    ],
    answer_generator: Annotated[
        AnswerGenerator,
        Depends(get_answer_generator),
    ],
) -> AnswerResponse:
    filters = (
        request.filters.model_dump(exclude_none=True)
        if request.filters is not None
        else {}
    )

    try:
        retrieval_results = retrieval_service.retrieve(
            RetrievalRequest(
                query=request.query,
                limit=ANSWER_RETRIEVAL_LIMIT,
                filters=filters,
            )
        )

        generated_answer = answer_generator.generate(
            question=request.query,
            results=retrieval_results,
        )
    except (
        RetrievalUnavailableError,
        LanguageModelError,
        ContextBudgetError,
        CitationValidationError,
    ) as exc:
        raise AnswerUnavailableError(
            "The answer workflow could not be completed."
        ) from exc

    return AnswerResponse(
        query=request.query,
        answer=generated_answer.answer,
        sources=[
            AnswerSource(
                citation_id=source.citation_id,
                chunk_id=source.chunk.chunk_id,
                document_id=source.chunk.document_id,
                title=source.chunk.title,
                heading_path=source.chunk.heading_path,
                anchor=source.chunk.anchor,
                excerpt=source.chunk.text,
                url=source.chunk.url,
            )
            for source in generated_answer.sources
        ],
        sufficient_evidence=generated_answer.sufficient_evidence,
    )
