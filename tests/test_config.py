from rag_service.config import Settings


def test_wordpress_settings_have_expected_defaults() -> None:
    settings = Settings(
        wordpress_base_url="https://example.com",
        _env_file=None,
    )

    assert settings.wordpress_base_url == "https://example.com"
    assert settings.wordpress_api_path == "/wp-json/wp/v2"
    assert settings.wordpress_request_timeout == 10.0
    assert settings.wordpress_page_size == 100