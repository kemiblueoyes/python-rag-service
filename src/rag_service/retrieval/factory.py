from rag_service.config import Settings
from rag_service.embeddings import create_embedding_provider
from rag_service.retrieval.service import RetrievalService
from rag_service.vectorstores import create_vector_store


def create_retrieval_service(settings: Settings) -> RetrievalService:
    """Build the configured retrieval service."""

    return RetrievalService(
        embedding_provider=create_embedding_provider(settings),
        vector_store=create_vector_store(settings),
        min_score=settings.retrieval_min_score,
    )