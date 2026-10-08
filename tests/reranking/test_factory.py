import pytest

from rag_service.config import Settings
from rag_service.errors import ServiceConfigurationError
from rag_service.reranking import (
    VoyageReranker,
    create_reranker,
)


def test_create_reranker_creates_voyage_provider() -> None:
    settings = Settings(
        reranking_provider="voyage",
        reranking_model="rerank-2.5",
        voyage_api_key="test-key",
    )

    reranker = create_reranker(settings)

    assert isinstance(
        reranker,
        VoyageReranker,
    )


def test_create_reranker_rejects_unknown_provider() -> None:
    settings = Settings(
        reranking_provider="unknown",
    )

    with pytest.raises(
        ServiceConfigurationError,
        match="Set RERANKING_PROVIDER to voyage",
    ):
        create_reranker(settings)