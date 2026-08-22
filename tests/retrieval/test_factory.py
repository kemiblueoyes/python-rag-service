from unittest.mock import MagicMock

from pytest import MonkeyPatch

from rag_service.config import Settings
from rag_service.retrieval.factory import create_retrieval_service


def test_create_retrieval_service_builds_configured_dependencies(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = Settings(retrieval_min_score=0.42)

    embedding_provider = MagicMock()
    vector_store = MagicMock()
    retrieval_service = MagicMock()

    embedding_factory = MagicMock(return_value=embedding_provider)
    vector_store_factory = MagicMock(return_value=vector_store)
    service_factory = MagicMock(return_value=retrieval_service)

    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_embedding_provider",
        embedding_factory,
    )
    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_vector_store",
        vector_store_factory,
    )
    monkeypatch.setattr(
        "rag_service.retrieval.factory.RetrievalService",
        service_factory,
    )

    result = create_retrieval_service(settings)

    assert result is retrieval_service

    embedding_factory.assert_called_once_with(settings)
    vector_store_factory.assert_called_once_with(settings)

    service_factory.assert_called_once_with(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        min_score=0.42,
    )