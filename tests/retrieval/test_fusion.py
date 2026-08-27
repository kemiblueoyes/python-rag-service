import pytest

from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval.fusion import (
    reciprocal_rank_fusion,
)
from rag_service.vectorstores.base import SearchResult


def _result(
    chunk_id: str,
    score: float,
) -> SearchResult:
    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id=chunk_id.split(":chunk:")[0],
        source="wordpress",
        source_id=chunk_id,
        title=chunk_id,
        url=f"https://example.test/{chunk_id}",
        content_type="page",
        text="Example retrieval content.",
        heading_path=[],
        sequence=0,
    )

    return SearchResult(
        chunk=chunk,
        score=score,
    )


def test_rrf_combines_rankings() -> None:
    shared = _result(
        "wordpress:page:1:chunk:0",
        0.90,
    )
    semantic_only = _result(
        "wordpress:page:2:chunk:0",
        0.80,
    )
    lexical_only = _result(
        "wordpress:page:3:chunk:0",
        4.50,
    )

    fused = reciprocal_rank_fusion(
        [
            [
                shared,
                semantic_only,
            ],
            [
                shared,
                lexical_only,
            ],
        ],
        k=60,
    )

    assert [
        item.result.chunk.chunk_id
        for item in fused
    ] == [
        shared.chunk.chunk_id,
        semantic_only.chunk.chunk_id,
        lexical_only.chunk.chunk_id,
    ]


def test_rrf_rewards_results_present_in_multiple_lists() -> None:
    shared = _result(
        "wordpress:page:1:chunk:0",
        0.90,
    )
    other = _result(
        "wordpress:page:2:chunk:0",
        0.80,
    )

    fused = reciprocal_rank_fusion(
        [
            [
                shared,
                other,
            ],
            [
                shared,
            ],
        ],
        k=60,
    )

    assert fused[0].result.chunk.chunk_id == shared.chunk.chunk_id
    assert fused[0].score > fused[1].score


def test_rrf_uses_rank_not_original_score() -> None:
    high_vector_score = _result(
        "wordpress:page:1:chunk:0",
        0.99,
    )
    low_vector_score = _result(
        "wordpress:page:2:chunk:0",
        0.10,
    )

    fused = reciprocal_rank_fusion(
        [
            [
                high_vector_score,
                low_vector_score,
            ]
        ],
        k=60,
    )

    assert fused[0].score == pytest.approx(
        1 / 61
    )
    assert fused[1].score == pytest.approx(
        1 / 62
    )


def test_rrf_returns_empty_for_empty_result_sets() -> None:
    assert reciprocal_rank_fusion(
        [[], []],
        k=60,
    ) == []


def test_rrf_rejects_invalid_constant() -> None:
    with pytest.raises(
        ValueError,
        match="RRF constant must be at least 1",
    ):
        reciprocal_rank_fusion(
            [[]],
            k=0,
        )