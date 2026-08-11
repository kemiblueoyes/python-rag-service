from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Application-facing contract for retrieval embeddings."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed content that will be stored in the retrieval index."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed one search query in the same vector space as documents."""
        ...
