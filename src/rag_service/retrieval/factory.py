from rag_service.client_lifecycle import close_client
from rag_service.config import Settings
from rag_service.embeddings import (
    create_embedding_provider,
)
from rag_service.errors import ServiceConfigurationError
from rag_service.lexical import (
    create_lexical_retriever,
)
from rag_service.provider_failures import retrieval_exception_for
from rag_service.reranking import (
    create_reranker,
)
from rag_service.retrieval.service import (
    RetrievalService,
)
from rag_service.vectorstores import (
    create_vector_store,
)


def create_retrieval_service(
    settings: Settings,
) -> RetrievalService:
    """Build the configured retrieval service."""

    try:
        return _build_retrieval_service(settings)
    except ServiceConfigurationError:
        raise
    except Exception as exc:
        replacement = retrieval_exception_for(exc)
        if replacement is None:
            raise
        raise replacement from None


def _build_retrieval_service(settings: Settings) -> RetrievalService:
    created: list[object] = []
    try:
        embedding_provider = create_embedding_provider(settings)
        created.append(embedding_provider)
        vector_store = create_vector_store(settings)
        created.append(vector_store)
        lexical_retriever = create_lexical_retriever(settings)
        created.append(lexical_retriever)
        reranker = create_reranker(settings)
        created.append(reranker)
        return RetrievalService(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            lexical_retriever=lexical_retriever,
            reranker=reranker,
            vector_candidate_depth=(
                settings.retrieval_vector_candidate_depth
            ),
            lexical_candidate_depth=(
                settings.retrieval_lexical_candidate_depth
            ),
            fused_candidate_depth=(
                settings.retrieval_fused_candidate_depth
            ),
            rrf_k=settings.retrieval_rrf_k,
            support_cutoff=(
                settings.retrieval_support_cutoff
            ),
        )
    except Exception:
        for resource in reversed(created):
            close_client(resource, operation="retrieval")
        raise