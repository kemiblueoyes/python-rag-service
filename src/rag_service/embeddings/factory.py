from rag_service.config import Settings
from rag_service.embeddings.base import EmbeddingProvider
from rag_service.embeddings.voyage import VoyageEmbeddingProvider
from rag_service.errors import ServiceConfigurationError


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Create the embedding provider selected in settings."""

    if settings.embedding_provider == "voyage":
        return VoyageEmbeddingProvider(
            model=settings.embedding_model,
            api_key=settings.voyage_api_key,
            timeout=settings.voyage_timeout_seconds,
            max_retries=settings.voyage_max_retries,
        )
    raise ServiceConfigurationError(
        operation="retrieval",
        reason="unsupported_embedding_provider",
        diagnostic="Set EMBEDDING_PROVIDER to voyage.",
    )
