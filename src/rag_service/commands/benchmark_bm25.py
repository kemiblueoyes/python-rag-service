"""Measure local BM25 index construction and search.

The command builds synthetic chunks and does not call Voyage, Qdrant, or
OpenAI. It prints median times for construction, unfiltered search, and
filtered search. Those times depend on the machine. The test suite does
not compare them to a threshold.

Run it with:

    uv run python -m rag_service.commands.benchmark_bm25
"""

from collections.abc import Sequence
from statistics import median
from time import perf_counter

from rag_service.lexical.bm25 import Bm25Retriever
from rag_service.models.chunk import DocumentChunk

CORPUS_SIZES = (250, 1_000, 4_000)
CONSTRUCTION_REPEATS = 3
SEARCH_REPEATS = 10
SEARCH_LIMIT = 20


def main() -> None:
    """Print median construction and search times for each corpus size."""

    print(
        "size construction_median_ms "
        "unfiltered_median_ms filtered_median_ms"
    )
    for size in CORPUS_SIZES:
        chunks = _chunks(size)
        construction = _construction_times(chunks)
        retriever = Bm25Retriever(chunks)
        unfiltered = _search_times(
            retriever,
            filters=None,
        )
        filtered = _search_times(
            retriever,
            filters={"content_type": "glossary"},
        )
        print(
            f"{size} {_milliseconds(construction):.2f} "
            f"{_milliseconds(unfiltered):.2f} "
            f"{_milliseconds(filtered):.2f}"
        )


def _chunks(size: int) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for index in range(size):
        content_type = "glossary" if index % 20 == 0 else "page"
        chunks.append(
            DocumentChunk(
                chunk_id=f"benchmark:doc:{index}:chunk:0",
                document_id=f"benchmark:doc:{index}",
                source="benchmark",
                source_id=str(index),
                title=f"Benchmark document {index}",
                url=f"https://example.test/benchmark/{index}",
                content_type=content_type,
                text=(
                    f"alpha beta gamma keyword document {index} "
                    f"{'keyword ' * (index % 7)}"
                ),
                heading_path=["Benchmark"],
                sequence=0,
            )
        )
    return chunks


def _construction_times(
    chunks: Sequence[DocumentChunk],
) -> list[float]:
    samples: list[float] = []
    for _ in range(CONSTRUCTION_REPEATS):
        started = perf_counter()
        Bm25Retriever(chunks)
        samples.append(perf_counter() - started)
    return samples


def _search_times(
    retriever: Bm25Retriever,
    *,
    filters: dict[str, str] | None,
) -> list[float]:
    retriever.search(
        "keyword",
        limit=SEARCH_LIMIT,
        filters=filters,
    )
    samples: list[float] = []
    for _ in range(SEARCH_REPEATS):
        started = perf_counter()
        retriever.search(
            "keyword",
            limit=SEARCH_LIMIT,
            filters=filters,
        )
        samples.append(perf_counter() - started)
    return samples


def _milliseconds(samples: Sequence[float]) -> float:
    return median(samples) * 1_000


if __name__ == "__main__":
    main()
