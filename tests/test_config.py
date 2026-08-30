from rag_service.config import Settings


def test_wordpress_settings_have_expected_defaults() -> None:
    settings = Settings(  # type: ignore[call-arg]
        wordpress_base_url="https://example.com",
        _env_file=None,
    )

    assert settings.wordpress_base_url == "https://example.com"
    assert settings.wordpress_api_path == "/wp-json/wp/v2"
    assert settings.wordpress_request_timeout == 10.0
    assert settings.wordpress_page_size == 100
    assert settings.wordpress_collections == ("posts", "pages")
    assert settings.wordpress_profile == "default"


def test_wordpress_collections_can_include_custom_post_types() -> None:
    settings = Settings(  # type: ignore[call-arg]
        wordpress_base_url="https://example.com",
        wordpress_collections=("posts", "pages", "glossary"),
        _env_file=None,
    )

    assert settings.wordpress_collections == ("posts", "pages", "glossary")


def test_retrieval_provider_settings_have_expected_defaults() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.embedding_provider == "voyage"
    assert settings.embedding_model == "voyage-4-lite"
    assert settings.embedding_dimension == 1024
    assert settings.embedding_batch_size == 128
    assert settings.vector_database == "qdrant"
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection == "rag_chunks"

def test_generation_settings_have_expected_defaults() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.generation_provider == "openai"
    assert settings.generation_model == "gpt-5.6-terra"
    assert settings.generation_reasoning_effort == "low"
    assert settings.generation_context_budget_tokens == 8_000
    assert settings.generation_max_output_tokens == 1_000
    assert settings.openai_api_key is None
    assert settings.rag_api_key is None