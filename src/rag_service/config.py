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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
