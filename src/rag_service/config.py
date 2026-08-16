from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "python-rag-service"
    environment: str = "development"
    log_level: str = "INFO"

    # WordPress connector
    wordpress_base_url: str | None = None
    wordpress_api_path: str = "/wp-json/wp/v2"
    wordpress_request_timeout: float = 10.0
    wordpress_page_size: int = 100
    wordpress_collections: tuple[str, ...] = ("posts", "pages")
    wordpress_profile: str = "default"

    # Embeddings
    embedding_provider: str = "voyage"
    embedding_model: str = "voyage-4-lite"
    embedding_dimension: int = 1024
    embedding_batch_size: int = 128
    voyage_api_key: str | None = None

    # Vector storage
    vector_database: str = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "rag_chunks"

    # Retrieval
    retrieval_min_score: float = 0.50

    # Answer generation
    generation_provider: Literal["openai"] = "openai"
    generation_model: str = "gpt-5.6-terra"
    generation_reasoning_effort: Literal[
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    ] = "low"
    generation_context_budget_tokens: int = 8_000
    generation_max_output_tokens: int = 1_000
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
