from rag_service.config import Settings
from rag_service.vectorstores.base import VectorStore
from rag_service.vectorstores.qdrant import QdrantVectorStore


def create_vector_store(settings: Settings) -> VectorStore:
    """Build the configured vector-store adapter at the composition boundary."""

    if settings.vector_database == "qdrant":
        return QdrantVectorStore(
            collection_name=settings.qdrant_collection,
            vector_size=settings.embedding_dimension,
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    raise ValueError(f"Unsupported vector database: {settings.vector_database!r}")
