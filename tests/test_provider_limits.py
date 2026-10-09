import logging
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from rag_service.config import Settings, SettingsLoadError, load_settings, settings
from rag_service.embeddings.voyage import VoyageEmbeddingProvider
from rag_service.generation.providers.openai import OpenAILanguageModel
from rag_service.logging_config import configure_logging
from rag_service.reranking.voyage import VoyageReranker
from rag_service.vectorstores.qdrant import QdrantVectorStore

CANARY = "sk-secret-timeout"


@pytest.fixture
def log_stream() -> StringIO:
    stream = StringIO()
    configure_logging("INFO", stream=stream)
    yield stream
    configure_logging(settings.log_level)


def test_provider_limit_defaults() -> None:
    loaded = Settings(_env_file=None)

    assert loaded.voyage_timeout_seconds == 60.0
    assert loaded.voyage_max_retries == 0
    assert loaded.qdrant_timeout_seconds == 5
    assert loaded.openai_timeout_seconds == 120.0
    assert loaded.openai_max_retries == 0


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("VOYAGE_TIMEOUT_SECONDS", "nan"),
        ("VOYAGE_TIMEOUT_SECONDS", "inf"),
        ("VOYAGE_TIMEOUT_SECONDS", "-inf"),
        ("VOYAGE_TIMEOUT_SECONDS", "0.0"),
        ("VOYAGE_TIMEOUT_SECONDS", "-1"),
        ("OPENAI_TIMEOUT_SECONDS", "NaN"),
        ("OPENAI_TIMEOUT_SECONDS", "Infinity"),
        ("QDRANT_TIMEOUT_SECONDS", "0"),
        ("QDRANT_TIMEOUT_SECONDS", "1.5"),
        ("QDRANT_TIMEOUT_SECONDS", "inf"),
        ("VOYAGE_MAX_RETRIES", "-1"),
        ("VOYAGE_MAX_RETRIES", "3"),
        ("OPENAI_MAX_RETRIES", "4"),
        ("VOYAGE_TIMEOUT_SECONDS", CANARY),
    ],
)
def test_invalid_provider_limits_use_settings_diagnostics(
    name: str,
    value: str,
    log_stream: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv(name, value)

    with caplog.at_level(logging.ERROR, logger="rag_service.config"):
        with pytest.raises(SettingsLoadError) as raised:
            load_settings()

    message = str(raised.value)
    rendered = log_stream.getvalue()
    record = next(
        item for item in caplog.records if item.name == "rag_service.config"
    )
    assert name in message
    assert name in rendered
    assert "operation=settings" in rendered
    assert "reason=invalid_configuration" in rendered
    assert value not in message
    assert value not in record.getMessage()
    assert record.exc_info is None
    assert all(item.exc_info is None for item in caplog.records)
    if name.endswith("_TIMEOUT_SECONDS") and name != "QDRANT_TIMEOUT_SECONDS":
        assert "finite number of seconds greater than 0" in message
    elif name == "QDRANT_TIMEOUT_SECONDS":
        assert "whole number of seconds of at least 1" in message
    else:
        assert "integer from 0 through 2" in message


def test_factories_pass_timeout_and_retry_settings() -> None:
    loaded = Settings(
        _env_file=None,
        voyage_api_key="voyage-test",
        voyage_timeout_seconds=12.5,
        voyage_max_retries=2,
        qdrant_timeout_seconds=9,
        openai_api_key="openai-test",
        openai_timeout_seconds=33.0,
        openai_max_retries=1,
        generation_model="gpt-5.6-terra",
    )

    with (
        patch("voyageai.client.Client") as voyage,
        patch("rag_service.vectorstores.qdrant.QdrantClient") as qdrant,
        patch("rag_service.generation.providers.openai.OpenAI") as openai,
    ):
        from rag_service.embeddings.factory import create_embedding_provider
        from rag_service.reranking.factory import create_reranker
        from rag_service.vectorstores.factory import create_vector_store

        create_embedding_provider(loaded)
        create_reranker(loaded)
        create_vector_store(loaded)
        model = OpenAILanguageModel(
            model=loaded.generation_model,
            api_key=loaded.openai_api_key,
            timeout=loaded.openai_timeout_seconds,
            max_retries=loaded.openai_max_retries,
        )
        model._require_client()

    assert voyage.call_count == 2
    for call in voyage.call_args_list:
        assert call.kwargs["timeout"] == 12.5
        assert call.kwargs["max_retries"] == 2
    qdrant.assert_called_once()
    assert qdrant.call_args.kwargs["timeout"] == 9
    openai.assert_called_once_with(
        api_key="openai-test",
        timeout=33.0,
        max_retries=1,
    )


def test_voyage_sdk_has_no_public_close_method() -> None:
    from voyageai.client import Client

    assert not hasattr(Client, "close")


def test_owned_qdrant_client_closes_once_and_borrowed_client_stays_open() -> None:
    borrowed = MagicMock()
    borrowed_store = QdrantVectorStore(
        collection_name="chunks",
        vector_size=2,
        client=borrowed,
    )
    borrowed_store.close()
    borrowed.close.assert_not_called()

    owned = MagicMock()
    with patch(
        "rag_service.vectorstores.qdrant.QdrantClient",
        return_value=owned,
    ) as qdrant:
        store = QdrantVectorStore(
            collection_name="chunks",
            vector_size=2,
            url="http://localhost:6333",
            timeout=5,
        )
    qdrant.assert_called_once_with(
        url="http://localhost:6333",
        api_key=None,
        timeout=5,
    )
    store.close()
    store.close()
    owned.close.assert_called_once()


def test_owned_openai_client_closes_and_borrowed_client_stays_open() -> None:
    borrowed = MagicMock()
    borrowed_model = OpenAILanguageModel(
        model="gpt-5.6-terra",
        api_key="test-key",
        client=borrowed,
    )
    borrowed_model.close()
    borrowed.close.assert_not_called()
    assert borrowed_model._require_client() is borrowed

    owned = MagicMock()
    with patch(
        "rag_service.generation.providers.openai.OpenAI",
        return_value=owned,
    ):
        model = OpenAILanguageModel(
            model="gpt-5.6-terra",
            api_key="test-key",
            timeout=15.0,
            max_retries=0,
        )
        assert model._require_client() is owned
        model.close()
        with pytest.raises(RuntimeError, match="language model client is closed"):
            model._require_client()
    owned.close.assert_called_once()


def test_voyage_close_leaves_the_sdk_client_open() -> None:
    sdk = MagicMock()
    with patch("voyageai.client.Client", return_value=sdk):
        embedding = VoyageEmbeddingProvider(
            api_key="voyage-test",
            timeout=8.0,
            max_retries=0,
        )
        reranker = VoyageReranker(
            api_key="voyage-test",
            timeout=8.0,
            max_retries=0,
        )
    embedding.close()
    reranker.close()
    sdk.close.assert_not_called()

    injected = MagicMock()
    VoyageEmbeddingProvider(client=injected).close()
    VoyageReranker(client=injected).close()
    injected.close.assert_not_called()
