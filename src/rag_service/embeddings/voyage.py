from typing import Any, Protocol, cast


class _EmbeddingResponse(Protocol):
    embeddings: list[list[float]]


class _VoyageClient(Protocol):
    def embed(
        self,
        texts: list[str],
        *,
        model: str,
        input_type: str,
    ) -> _EmbeddingResponse: ...


class VoyageEmbeddingProvider:
    """Voyage AI adapter for document and query embeddings."""

    def __init__(
        self,
        *,
        model: str = "voyage-4-lite",
        api_key: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 0,
        client: _VoyageClient | None = None,
    ) -> None:
        self._owns_client = client is None
        if client is None:
            from voyageai.client import Client

            client = cast(
                _VoyageClient,
                Client(
                    api_key=api_key,
                    timeout=timeout,
                    max_retries=max_retries,
                ),
            )

        self._client = client
        self._model = model

    def close(self) -> None:
        """Release ownership of a client this adapter constructed.

        voyageai 0.5.0 Client has no public close method. Its HTTP
        session stays in the SDK's thread-local storage. An injected
        client stays open.
        """

        if not self._owns_client:
            return
        self._owns_client = False

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embed(
            texts,
            model=self._model,
            input_type="document",
        )
        return self._as_float_vectors(response.embeddings)

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Query text must not be empty.")
        response = self._client.embed(
            [text],
            model=self._model,
            input_type="query",
        )
        vectors = self._as_float_vectors(response.embeddings)
        if len(vectors) != 1:
            raise RuntimeError("Voyage returned an unexpected number of query vectors.")
        return vectors[0]

    @staticmethod
    def _as_float_vectors(vectors: Any) -> list[list[float]]:
        return [[float(value) for value in vector] for vector in vectors]
