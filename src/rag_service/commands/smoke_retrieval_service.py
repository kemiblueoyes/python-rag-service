"""Smoke test the live Phase 5 retrieval-service path against indexed content."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag_service.config import settings
from rag_service.retrieval import (
    RetrievalRequest,
    create_retrieval_service,
)

OUTPUT_PATH = Path("data/retrieval_smoke_results.md")

SMOKE_QUERIES: list[dict[str, Any]] = [
    {
        "label": "Terminology mismatch",
        "query": "Why can inconsistent terminology cause AI retrieval to fail?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Chunking",
        "query": "Why is heading-aware chunking useful for documentation retrieval?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Metadata",
        "query": "How can metadata improve AI retrieval?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "BM25",
        "query": "What is BM25 and how does it relate to semantic search?",
        "filters": {"source": "wordpress"},
    },
    {
    "label": "RAG basics",
    "query": "What is retrieval-augmented generation?",
    "filters": {"source": "wordpress"},
    },
    {
        "label": "Chunking failure",
        "query": "How can poor chunking reduce retrieval quality?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Embeddings",
        "query": "What role do embeddings play in semantic search?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Documentation engineering",
        "query": "What does a documentation engineer do?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Doc engineering",
        "query": "What is documentation engineering?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Context",
        "query": "How important is context in documentation?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "CMS statement",
        "query": "Choosing a CMS for documentation",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "CMS question",
        "query": "How do I choose a CMS for documentation?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Out-of-domain cooking",
        "query": "How long should I roast a whole chicken?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Out-of-domain finance",
        "query": "How do I calculate mortgage amortization?",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Out-of-domain Kubernetes",
        "query": "How do I configure Kubernetes horizontal pod autoscaling?",
        "filters": {"source": "wordpress"},
    },
        {
        "label": "Out-of-domain becoming a developer",
        "query": "How do I transition from technical writer to software developer",
        "filters": {"source": "wordpress"},
    },
    {
        "label": "Out-of-domain communication with spouse",
        "query": "How do I communicate effectively with my spouse?",
        "filters": {"source": "wordpress"},
    },
]


def _format_result(rank: int, result: Any) -> list[str]:
    chunk = result.chunk
    heading = " > ".join(chunk.heading_path) or "(none)"

    return [
        f"### #{rank} — score {result.score:.6f}",
        "",
        f"**Title:** {chunk.title}",
        "",
        f"**Heading:** {heading}",
        "",
        f"**URL:** {chunk.url}",
        "",
        f"**Chunk ID:** `{chunk.chunk_id}`",
        "",
        "**Text:**",
        "",
        chunk.text,
        "",
    ]


def main() -> None:
    if not settings.voyage_api_key:
        raise ValueError("VOYAGE_API_KEY must be configured.")

    if (
        not settings.qdrant_api_key
        and not settings.qdrant_url.startswith("http://localhost")
    ):
        raise ValueError(
            "QDRANT_API_KEY must be configured when using a remote Qdrant instance."
        )

    service = create_retrieval_service(settings)

    report: list[str] = [
        "# Retrieval Service Smoke Test",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        f"Collection: `{settings.qdrant_collection}`",
        "",
        f"Support cutoff: `{settings.retrieval_support_cutoff:.2f}`",
        "",
        (
            "Each query returns the five highest-ranked chunks "
            "from the live retrieval index."
        ),
        "",
    ]

    for test_number, smoke_query in enumerate(SMOKE_QUERIES, start=1):
        query = smoke_query["query"]
        filters = smoke_query["filters"]

        results = service.retrieve(
            RetrievalRequest(
                query=query,
                limit=5,
                filters=filters,
            )
        )

        if not results:
            report.extend(
                [
                    f"## Test {test_number}: {smoke_query['label']}",
                    "",
                    f"**Query:** {query}",
                    "",
                    f"**Filters:** `{filters}`",
                    "",
                    "**Results returned:** 0",
                    "",
                    (
                        "**Check:** PASS — no results passed the "
                        f"support cutoff of {settings.retrieval_support_cutoff:.2f}."
                    ),
                    "",
                    "---",
                    "",
                ]
            )
            continue

        previous_score: float | None = None
        for result in results:
            if previous_score is not None and result.score > previous_score:
                raise RuntimeError(
                    f"Results were not in descending rerank-score order for: {query}"
                )
            previous_score = result.score

        report.extend(
            [
                f"## Test {test_number}: {smoke_query['label']}",
                "",
                f"**Query:** {query}",
                "",
                f"**Filters:** `{filters}`",
                "",
                f"**Results returned:** {len(results)}",
                "",
            ]
        )

        for rank, result in enumerate(results, start=1):
            report.extend(_format_result(rank, result))

        report.extend(
            [
                "**Check:** PASS — results preserved descending similarity ranking.",
                "",
                "---",
                "",
            ]
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(report), encoding="utf-8")
    print(f"PASS: Retrieval smoke-test report written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()