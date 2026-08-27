from rag_service.config import Settings
from rag_service.embeddings import (
    create_embedding_provider,
)
from rag_service.lexical import (
    create_lexical_retriever,
)
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

    return RetrievalService(
        embedding_provider=(
            create_embedding_provider(settings)
        ),
        vector_store=create_vector_store(
            settings
        ),
        lexical_retriever=(
            create_lexical_retriever(settings)
        ),
        reranker=create_reranker(settings),
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