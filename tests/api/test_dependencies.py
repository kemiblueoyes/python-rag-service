from unittest.mock import MagicMock, patch

from rag_service.api.dependencies import get_retrieval_service
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