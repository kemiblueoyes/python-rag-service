from rag_service.config import Settings
from rag_service.errors import ServiceConfigurationError
from rag_service.reranking.base import Reranker
from rag_service.reranking.voyage import VoyageReranker


def create_reranker(
    settings: Settings,
) -> Reranker:
    """Create the reranker selected in settings."""

    if settings.reranking_provider == "voyage":
        return VoyageReranker(
            model=settings.reranking_model,
            api_key=settings.voyage_api_key,
        )

    raise ServiceConfigurationError(
        operation="retrieval",
        reason="unsupported_reranking_provider",
        diagnostic="Set RERANKING_PROVIDER to voyage.",
    )