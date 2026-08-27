from unittest.mock import MagicMock

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