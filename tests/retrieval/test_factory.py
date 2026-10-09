import logging
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from rag_service.config import Settings
from rag_service.retrieval.factory import create_retrieval_service


def test_create_retrieval_service_builds_configured_dependencies(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = Settings(
        retrieval_vector_candidate_depth=12,
        retrieval_lexical_candidate_depth=14,
        retrieval_fused_candidate_depth=10,
        retrieval_rrf_k=55,
        retrieval_support_cutoff=0.75,
    )

    embedding_provider = MagicMock()
    vector_store = MagicMock()
    lexical_retriever = MagicMock()
    reranker = MagicMock()
    retrieval_service = MagicMock()

    embedding_factory = MagicMock(
        return_value=embedding_provider
    )
    vector_store_factory = MagicMock(
        return_value=vector_store
    )
    lexical_factory = MagicMock(
        return_value=lexical_retriever
    )
    reranker_factory = MagicMock(
        return_value=reranker
    )
    service_factory = MagicMock(
        return_value=retrieval_service
    )

    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_embedding_provider",
        embedding_factory,
    )
    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_vector_store",
        vector_store_factory,
    )
    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_lexical_retriever",
        lexical_factory,
    )
    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_reranker",
        reranker_factory,
    )
    monkeypatch.setattr(
        "rag_service.retrieval.factory.RetrievalService",
        service_factory,
    )

    result = create_retrieval_service(settings)

    assert result is retrieval_service

    embedding_factory.assert_called_once_with(settings)
    vector_store_factory.assert_called_once_with(settings)
    lexical_factory.assert_called_once_with(settings)
    reranker_factory.assert_called_once_with(settings)

    service_factory.assert_called_once_with(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        lexical_retriever=lexical_retriever,
        reranker=reranker,
        vector_candidate_depth=12,
        lexical_candidate_depth=14,
        fused_candidate_depth=10,
        rrf_k=55,
        support_cutoff=0.75,
    )


def test_failed_initialization_closes_created_clients_without_logging_exception_text(
    monkeypatch: MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    canary = "sk-secret-cleanup"
    embedding_provider = MagicMock()
    vector_store = MagicMock()
    vector_store.close.side_effect = ValueError(canary)

    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_embedding_provider",
        MagicMock(return_value=embedding_provider),
    )
    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_vector_store",
        MagicMock(return_value=vector_store),
    )
    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_lexical_retriever",
        MagicMock(side_effect=RuntimeError("index failed")),
    )
    reranker_factory = MagicMock()
    monkeypatch.setattr(
        "rag_service.retrieval.factory.create_reranker",
        reranker_factory,
    )

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(RuntimeError, match="index failed"):
            create_retrieval_service(Settings(_env_file=None))

    embedding_provider.close.assert_called_once()
    vector_store.close.assert_called_once()
    reranker_factory.assert_not_called()
    cleanup = [
        record
        for record in caplog.records
        if record.name == "rag_service.client_lifecycle"
    ]
    assert len(cleanup) == 1
    assert cleanup[0].operation == "retrieval"
    assert cleanup[0].reason == "cleanup_failed"
    assert cleanup[0].exc_info is None
    assert canary not in caplog.text
    assert canary not in repr(cleanup[0].__dict__)