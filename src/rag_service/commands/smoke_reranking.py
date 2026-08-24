from pathlib import Path
from typing import Protocol, cast

from rag_service.config import settings
from rag_service.embeddings import create_embedding_provider
from rag_service.vectorstores import create_vector_store
from rag_service.vectorstores.base import SearchResult

QUERY = QUERY = (
    "How do I transition from technical writer to software developer"
)

CANDIDATE_DEPTH = 20
RERANK_MODEL = "rerank-2.5"

OUTPUT_PATH = Path("data/evaluation/reranking_smoke.md")


class _RerankingResult(Protocol):
    index: int
    relevance_score: float


class _RerankingResponse(Protocol):
    results: list[_RerankingResult]
    total_tokens: int


class _VoyageRerankClient(Protocol):
    def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        model: str,
        top_k: int | None = None,
        truncation: bool = True,
    ) -> _RerankingResponse: ...


def _document_for_reranking(result: SearchResult) -> str:
    heading = " > ".join(result.chunk.heading_path) or "(none)"

    return (
        f"Title: {result.chunk.title}\n"
        f"Heading: {heading}\n"
        f"Content:\n{result.chunk.text}"
    )


def main() -> None:
    """Compare vector ranking with Voyage reranking for one known failure."""

    if not settings.voyage_api_key:
        raise ValueError("VOYAGE_API_KEY must be configured.")

    if (
        not settings.qdrant_api_key
        and not settings.qdrant_url.startswith("http://localhost")
    ):
        raise ValueError(
            "QDRANT_API_KEY must be configured when using "
            "a remote Qdrant instance."
        )

    embedding_provider = create_embedding_provider(settings)
    vector_store = create_vector_store(settings)

    query_vector = embedding_provider.embed_query(QUERY)

    candidates = vector_store.search(
        query_vector=query_vector,
        limit=CANDIDATE_DEPTH,
        filters=None,
    )

    if not candidates:
        raise RuntimeError("Vector search returned no candidates.")

    documents = [
        _document_for_reranking(candidate)
        for candidate in candidates
    ]

    from voyageai.client import Client

    rerank_client = cast(
        _VoyageRerankClient,
        Client(api_key=settings.voyage_api_key),
    )

    response = rerank_client.rerank(
        QUERY,
        documents,
        model=RERANK_MODEL,
    )

    markdown = [
        "# Reranking Smoke Test",
        "",
        f"Query: {QUERY}",
        "",
        f"Embedding model: `{settings.embedding_model}`",
        "",
        f"Reranking model: `{RERANK_MODEL}`",
        "",
        f"Candidate depth: `{CANDIDATE_DEPTH}`",
        "",
        "## Reranked results",
        "",
    ]

    for rerank_rank, reranked in enumerate(
        response.results,
        start=1,
    ):
        if reranked.index < 0 or reranked.index >= len(candidates):
            raise RuntimeError(
                "Voyage returned an invalid candidate index."
            )

        candidate = candidates[reranked.index]
        heading = (
            " > ".join(candidate.chunk.heading_path)
            or "(none)"
        )

        markdown.extend(
            [
                (
                    f"{rerank_rank}. "
                    f"**{candidate.chunk.title}**"
                ),
                (
                    "   - Rerank score: "
                    f"`{reranked.relevance_score:.6f}`"
                ),
                (
                    "   - Original vector rank: "
                    f"`{reranked.index + 1}`"
                ),
                (
                    "   - Vector score: "
                    f"`{candidate.score:.6f}`"
                ),
                f"   - Heading: {heading}",
                f"   - Chunk: `{candidate.chunk.chunk_id}`",
                f"   - Text: {candidate.chunk.text}",
                "",
            ]
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print(
        "PASS: Reranking smoke test written to "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()