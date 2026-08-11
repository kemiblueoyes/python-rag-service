from rag_service.config import Settings
from rag_service.embeddings.base import EmbeddingProvider
from rag_service.embeddings.voyage import VoyageEmbeddingProvider


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Create the embedding provider selected in settings."""

    if settings.embedding_provider == "voyage":
        return VoyageEmbeddingProvider(
            model=settings.embedding_model,
            api_key=settings.voyage_api_key,
        )
    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider!r}")
