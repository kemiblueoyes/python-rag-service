"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    app_name: str = "python-rag-service"
    environment: str = "development"
    log_level: str = "INFO"
    openai_api_key: str | None = None
    vector_store_url: str | None = None


def get_settings() -> Settings:
    """Build settings from the current environment."""
    return Settings(
        app_name=os.getenv("APP_NAME", "python-rag-service"),
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        vector_store_url=os.getenv("VECTOR_STORE_URL"),
    )
