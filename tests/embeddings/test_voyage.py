from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from rag_service.embeddings.voyage import VoyageEmbeddingProvider


def test_embeds_documents_with_retrieval_input_type() -> None:
    client = MagicMock()
    client.embed.return_value = SimpleNamespace(embeddings=[[1, 2], [3, 4]])
    provider = VoyageEmbeddingProvider(model="voyage-4-lite", client=client)

    result = provider.embed_documents(["first", "second"])

    assert result == [[1.0, 2.0], [3.0, 4.0]]
    client.embed.assert_called_once_with(
        ["first", "second"],
        model="voyage-4-lite",
        input_type="document",
    )


def test_embeds_query_with_query_input_type() -> None:
    client = MagicMock()
    client.embed.return_value = SimpleNamespace(embeddings=[[1.5, 2.5]])
    provider = VoyageEmbeddingProvider(model="voyage-4-lite", client=client)

    assert provider.embed_query("how does this work?") == [1.5, 2.5]
    client.embed.assert_called_once_with(
        ["how does this work?"],
        model="voyage-4-lite",
        input_type="query",
    )


def test_rejects_empty_query() -> None:
    provider = VoyageEmbeddingProvider(client=MagicMock())

    with pytest.raises(ValueError, match="must not be empty"):
        provider.embed_query("  ")
