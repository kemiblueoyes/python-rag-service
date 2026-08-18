from unittest.mock import MagicMock, patch

from rag_service.api.dependencies import (
    get_answer_generator,
    get_retrieval_service,
)
from rag_service.generation import AnswerGenerator
from rag_service.retrieval import RetrievalService


def test_get_retrieval_service_is_cached() -> None:
    service = MagicMock(spec=RetrievalService)

    get_retrieval_service.cache_clear()

    with patch(
        "rag_service.api.dependencies.create_retrieval_service",
        return_value=service,
    ) as create_service:
        first = get_retrieval_service()
        second = get_retrieval_service()

    assert first is service
    assert second is service
    create_service.assert_called_once()

    get_retrieval_service.cache_clear()

def test_get_answer_generator_is_cached() -> None:
    generator = MagicMock(spec=AnswerGenerator)

    get_answer_generator.cache_clear()

    with patch(
        "rag_service.api.dependencies.create_answer_generator",
        return_value=generator,
    ) as create_generator:
        first = get_answer_generator()
        second = get_answer_generator()

    assert first is generator
    assert second is generator
    create_generator.assert_called_once()

    get_answer_generator.cache_clear()