from typing import Annotated

from fastapi import APIRouter, Depends

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
)

ANSWER_RETRIEVAL_LIMIT = 5


@router.post(
    "/answer",
    response_model=AnswerResponse,
    summary="Generate a grounded answer",
    description=(
        "Retrieve relevant documentation and generate an answer "
        "grounded in validated source content."
    ),
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Request validation failed.",
        },
        503: {
            "model": ErrorResponse,
            "description": "Answer generation is temporarily unavailable.",
        },
    },
)
def answer(
    request: AnswerRequest,
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