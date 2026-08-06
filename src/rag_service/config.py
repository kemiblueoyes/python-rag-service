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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
