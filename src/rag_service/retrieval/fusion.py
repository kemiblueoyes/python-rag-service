from dataclasses import dataclass

from rag_service.vectorstores.base import SearchResult


@dataclass(frozen=True, slots=True)
class FusedSearchResult:
    result: SearchResult
    score: float


def reciprocal_rank_fusion(
    result_sets: list[list[SearchResult]],
    *,
    k: int = 60,
) -> list[FusedSearchResult]:
    """Fuse ranked result lists with Reciprocal Rank Fusion."""

    if k < 1:
        raise ValueError("RRF constant must be at least 1.")

    scores: dict[str, float] = {}
    results_by_chunk_id: dict[str, SearchResult] = {}

    for results in result_sets:
        for rank, result in enumerate(
            results,
            start=1,
        ):
            chunk_id = result.chunk.chunk_id

            scores[chunk_id] = (
                scores.get(chunk_id, 0.0)
                + 1.0 / (k + rank)
            )

            results_by_chunk_id.setdefault(
                chunk_id,
                result,
            )

    fused = [
        FusedSearchResult(
            result=results_by_chunk_id[chunk_id],
            score=score,
        )
        for chunk_id, score in scores.items()
    ]

    return sorted(
        fused,
        key=lambda item: item.score,
        reverse=True,
    )