from functools import lru_cache

from rag_service.config import settings
from rag_service.retrieval import RetrievalService, create_retrieval_service


@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """Return the configured retrieval service used by API endpoints."""
    return create_retrieval_service(settings)