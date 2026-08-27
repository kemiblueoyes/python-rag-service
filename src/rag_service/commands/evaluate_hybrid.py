"""Evaluate hybrid vector + BM25 retrieval using Reciprocal Rank Fusion.

This experiment:
- Retrieves 20 semantic candidates without the current 0.50 cutoff.
- Retrieves 20 BM25 candidates from the full Qdrant chunk corpus.
- Combines both ranked lists with Reciprocal Rank Fusion (RRF).
- Evaluates the top five fused results against the gold dataset.
- Records vector rank/score, BM25 rank/score, and fused RRF score.
- Does not apply or invent an RRF score cutoff.
- Labels expected-empty cases CUTOFF NOT EVALUATED.
"""

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import bm25s  # type: ignore[import-untyped]
from qdrant_client import QdrantClient

from rag_service.config import settings
from rag_service.embeddings import create_embedding_provider
from rag_service.evaluation.dataset import load_evaluation_dataset
from rag_service.evaluation.models import (
    EvaluationCase,
    GoldSource,
    NonRelevantSource,
)
from rag_service.evaluation.retrieval import (
    RetrievalEvaluationResult,
    evaluate_retrieval_case,
)
from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval.models import RetrievalResult
from rag_service.vectorstores import create_vector_store
from rag_service.vectorstores.base import SearchResult

DATASET_PATH = Path("evaluation/datasets/baseline.json")
OUTPUT_DIRECTORY = Path("data/evaluation")
JSON_OUTPUT_PATH = OUTPUT_DIRECTORY / "hybrid_evaluation.json"
MARKDOWN_OUTPUT_PATH = OUTPUT_DIRECTORY / "hybrid_evaluation.md"

CANDIDATE_DEPTH = 20
EVALUATION_DEPTH = 5
RRF_K = 60
SCROLL_BATCH_SIZE = 256


@dataclass
class _HybridCandidate:
    chunk: DocumentChunk
    vector_rank: int | None = None
    vector_score: float | None = None
    bm25_rank: int | None = None
    bm25_score: float | None = None
    rrf_score: float = 0.0


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value * 100:.1f}%"


def _document_for_bm25(chunk: DocumentChunk) -> str:
    heading = " > ".join(chunk.heading_path)
    parts = [chunk.title, heading, chunk.text]

    return "\n".join(part for part in parts if part)


def _load_chunks() -> list[DocumentChunk]:
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )

    chunks: list[DocumentChunk] = []
    seen_chunk_ids: set[str] = set()
    offset: Any = None

    while True:
        points, next_offset = client.scroll(
            collection_name=settings.qdrant_collection,
            limit=SCROLL_BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        for point in points:
            if not isinstance(point.payload, Mapping):
                raise RuntimeError(
                    "Qdrant point is missing its chunk payload."
                )

            chunk = DocumentChunk.model_validate(dict(point.payload))

            if chunk.chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(chunk.chunk_id)
            chunks.append(chunk)

        if next_offset is None:
            break

        offset = next_offset

    if not chunks:
        raise RuntimeError(
            "No chunks were found in the configured Qdrant collection."
        )

    return chunks


def _matches_filters(
    chunk: DocumentChunk,
    filters: dict[str, str | list[str]],
) -> bool:
    for key, expected in filters.items():
        if not hasattr(chunk, key):
            raise ValueError(
                f"Unsupported hybrid evaluation filter: {key}"
            )

        actual = getattr(chunk, key)

        if isinstance(expected, str):
            if actual != expected:
                return False
            continue

        if actual not in expected:
            return False

    return True


def _deduplicate_vector_candidates(
    results: list[SearchResult],
) -> list[SearchResult]:
    seen_chunk_ids: set[str] = set()
    unique_results: list[SearchResult] = []

    for result in results:
        chunk_id = result.chunk.chunk_id

        if chunk_id in seen_chunk_ids:
            continue

        seen_chunk_ids.add(chunk_id)
        unique_results.append(result)

    return unique_results


def _retrieve_bm25_candidates(
    *,
    retriever: Any,
    chunks: list[DocumentChunk],
    case: EvaluationCase,
) -> list[tuple[DocumentChunk, float]]:
    query_tokens = bm25s.tokenize(
        [case.query],
        stopwords="en",
    )

    document_ids, scores = retriever.retrieve(
        query_tokens,
        k=len(chunks),
    )

    results: list[tuple[DocumentChunk, float]] = []

    for position in range(document_ids.shape[1]):
        chunk_index = int(document_ids[0, position])
        chunk = chunks[chunk_index]

        if not _matches_filters(chunk, case.filters):
            continue

        results.append(
            (
                chunk,
                float(scores[0, position]),
            )
        )

        if len(results) >= CANDIDATE_DEPTH:
            break

    return results


def _fuse_candidates(
    vector_results: list[SearchResult],
    bm25_results: list[tuple[DocumentChunk, float]],
) -> list[_HybridCandidate]:
    candidates: dict[str, _HybridCandidate] = {}

    for rank, result in enumerate(vector_results, start=1):
        chunk_id = result.chunk.chunk_id
        candidate = candidates.setdefault(
            chunk_id,
            _HybridCandidate(chunk=result.chunk),
        )
        candidate.vector_rank = rank
        candidate.vector_score = result.score
        candidate.rrf_score += 1.0 / (RRF_K + rank)

    for rank, (chunk, score) in enumerate(bm25_results, start=1):
        candidate = candidates.setdefault(
            chunk.chunk_id,
            _HybridCandidate(chunk=chunk),
        )
        candidate.bm25_rank = rank
        candidate.bm25_score = score
        candidate.rrf_score += 1.0 / (RRF_K + rank)

    return sorted(
        candidates.values(),
        key=lambda candidate: (
            candidate.rrf_score,
            -(
                candidate.vector_rank
                if candidate.vector_rank is not None
                else CANDIDATE_DEPTH + 1
            ),
            -(
                candidate.bm25_rank
                if candidate.bm25_rank is not None
                else CANDIDATE_DEPTH + 1
            ),
        ),
        reverse=True,
    )


def _matches_source(
    chunk: DocumentChunk,
    source: GoldSource | NonRelevantSource,
) -> bool:
    if source.chunk_id is not None:
        return chunk.chunk_id == source.chunk_id

    return (
        chunk.document_id == source.document_id
        and chunk.heading_path == source.heading_path
    )


def _judgment_for_chunk(
    case: EvaluationCase,
    chunk: DocumentChunk,
) -> str:
    for relevant_source in case.retrieval.relevant_sources:
        if _matches_source(chunk, relevant_source):
            return f"relevant ({relevant_source.role})"

    for nonrelevant_source in case.retrieval.nonrelevant_sources:
        if _matches_source(chunk, nonrelevant_source):
            return "nonrelevant"

    return "unjudged"


def _case_passed(
    case: EvaluationCase,
    evaluation: RetrievalEvaluationResult,
) -> bool:
    if case.category == "multi_section":
        required_primary_count = sum(
            source.role == "primary"
            for source in case.retrieval.relevant_sources
        )

        return evaluation.primary_retrieved_count == required_primary_count

    return evaluation.hit_at_k


def _summarize_answerable(
    evaluations: list[RetrievalEvaluationResult],
    passed_count: int,
) -> dict[str, Any]:
    if not evaluations:
        raise ValueError(
            "At least one answerable evaluation is required."
        )

    precision_values = [
        evaluation.precision_at_k
        for evaluation in evaluations
        if evaluation.precision_at_k is not None
    ]

    return {
        "answerable_cases": len(evaluations),
        "successful_answerable_cases": passed_count,
        "answerable_success_rate": passed_count / len(evaluations),
        "primary_hit_rate_at_5": (
            sum(evaluation.hit_at_k for evaluation in evaluations)
            / len(evaluations)
        ),
        "mean_precision_at_5": (
            sum(precision_values) / len(precision_values)
            if precision_values
            else None
        ),
        "precision_evaluable_cases": len(precision_values),
        "mean_recall_at_5": (
            sum(evaluation.recall_at_k for evaluation in evaluations)
            / len(evaluations)
        ),
        "mean_reciprocal_rank": (
            sum(
                evaluation.reciprocal_rank
                for evaluation in evaluations
            )
            / len(evaluations)
        ),
    }


def _format_optional_rank(value: int | None) -> str:
    return str(value) if value is not None else "—"


def _format_optional_score(value: float | None) -> str:
    return f"{value:.6f}" if value is not None else "—"


def main() -> None:
    """Run hybrid vector + BM25 evaluation across the gold dataset."""

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

    dataset = load_evaluation_dataset(DATASET_PATH)
    chunks = _load_chunks()

    corpus = [_document_for_bm25(chunk) for chunk in chunks]
    corpus_tokens = bm25s.tokenize(corpus, stopwords="en")

    bm25_retriever = bm25s.BM25()
    bm25_retriever.index(corpus_tokens)

    embedding_provider = create_embedding_provider(settings)
    vector_store = create_vector_store(settings)

    answerable_evaluations: list[
        RetrievalEvaluationResult
    ] = []
    case_reports: list[dict[str, Any]] = []
    passed_answerable_count = 0

    for case in dataset.cases:
        query_vector = embedding_provider.embed_query(case.query)

        vector_candidates = vector_store.search(
            query_vector=query_vector,
            limit=CANDIDATE_DEPTH,
            filters=case.filters or None,
        )
        vector_candidates = _deduplicate_vector_candidates(
            vector_candidates
        )

        bm25_candidates = _retrieve_bm25_candidates(
            retriever=bm25_retriever,
            chunks=chunks,
            case=case,
        )

        fused_candidates = _fuse_candidates(
            vector_candidates,
            bm25_candidates,
        )
        top_candidates = fused_candidates[:EVALUATION_DEPTH]

        hybrid_results = [
            RetrievalResult(
                chunk=candidate.chunk,
                score=candidate.rrf_score,
            )
            for candidate in top_candidates
        ]

        serialized_results = [
            {
                "hybrid_rank": rank,
                "rrf_score": candidate.rrf_score,
                "vector_rank": candidate.vector_rank,
                "vector_score": candidate.vector_score,
                "bm25_rank": candidate.bm25_rank,
                "bm25_score": candidate.bm25_score,
                "judgment": _judgment_for_chunk(
                    case,
                    candidate.chunk,
                ),
                "chunk_id": candidate.chunk.chunk_id,
                "document_id": candidate.chunk.document_id,
                "title": candidate.chunk.title,
                "heading_path": candidate.chunk.heading_path,
                "url": candidate.chunk.url,
                "text": candidate.chunk.text,
            }
            for rank, candidate in enumerate(top_candidates, start=1)
        ]

        evaluation: RetrievalEvaluationResult | None
        passed: bool | None

        if case.retrieval.expect_empty:
            evaluation = None
            passed = None
        else:
            evaluation = evaluate_retrieval_case(
                case,
                hybrid_results,
                k=EVALUATION_DEPTH,
            )
            passed = _case_passed(case, evaluation)
            answerable_evaluations.append(evaluation)

            if passed:
                passed_answerable_count += 1

        case_reports.append(
            {
                "case_id": case.id,
                "category": case.category,
                "query": case.query,
                "expected_empty": case.retrieval.expect_empty,
                "evaluation": (
                    asdict(evaluation)
                    if evaluation is not None
                    else None
                ),
                "passed": passed,
                "hybrid_results": serialized_results,
                "notes": case.notes,
            }
        )

    summary = _summarize_answerable(
        answerable_evaluations,
        passed_answerable_count,
    )
    generated_at = datetime.now(UTC).isoformat()

    json_report = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.version,
        "generated_at": generated_at,
        "collection": settings.qdrant_collection,
        "embedding_model": settings.embedding_model,
        "corpus_size": len(chunks),
        "vector_candidate_depth": CANDIDATE_DEPTH,
        "bm25_candidate_depth": CANDIDATE_DEPTH,
        "evaluation_depth": EVALUATION_DEPTH,
        "fusion_method": "reciprocal_rank_fusion",
        "rrf_k": RRF_K,
        "rrf_score_cutoff": None,
        "summary": summary,
        "cases": case_reports,
    }

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    JSON_OUTPUT_PATH.write_text(
        json.dumps(
            json_report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    markdown: list[str] = [
        "# Hybrid Retrieval Evaluation",
        "",
        f"Generated: {generated_at}",
        "",
        f"Dataset: `{dataset.dataset_id}`",
        "",
        f"Dataset version: `{dataset.version}`",
        "",
        f"Collection: `{settings.qdrant_collection}`",
        "",
        f"Embedding model: `{settings.embedding_model}`",
        "",
        f"Indexed chunks: `{len(chunks)}`",
        "",
        f"Vector candidates per query: `{CANDIDATE_DEPTH}`",
        "",
        f"BM25 candidates per query: `{CANDIDATE_DEPTH}`",
        "",
        "Fusion method: `Reciprocal Rank Fusion (RRF)`",
        "",
        f"RRF constant: `{RRF_K}`",
        "",
        f"Fused results evaluated: `{EVALUATION_DEPTH}`",
        "",
        "**RRF score cutoff:** Not applied",
        "",
        (
            "Expected-empty cases are not marked pass or fail "
            "because no RRF score cutoff has been chosen."
        ),
        "",
        "## Answerable-case summary",
        "",
        (
            "- Answerable cases: "
            f"**{summary['answerable_cases']}**"
        ),
        (
            "- Successful answerable cases: "
            f"**{summary['successful_answerable_cases']}**"
        ),
        (
            "- Answerable success rate: "
            f"**{_format_percentage(summary['answerable_success_rate'])}**"
        ),
        (
            "- Primary hit rate@5: "
            f"**{_format_percentage(summary['primary_hit_rate_at_5'])}**"
        ),
        (
            "- Mean precision@5: "
            f"**{_format_percentage(summary['mean_precision_at_5'])}**"
        ),
        (
            "- Precision-evaluable answerable cases: "
            f"**{summary['precision_evaluable_cases']}"
            f"/{summary['answerable_cases']}**"
        ),
        (
            "- Mean recall@5: "
            f"**{_format_percentage(summary['mean_recall_at_5'])}**"
        ),
        (
            "- Mean reciprocal rank: "
            f"**{summary['mean_reciprocal_rank']:.3f}**"
        ),
        "",
        "## Case results",
        "",
    ]

    for case_report in case_reports:
        passed = case_report["passed"]

        if passed is None:
            status = "CUTOFF NOT EVALUATED"
        else:
            status = "PASS" if passed else "FAIL"

        markdown.extend(
            [
                f"### {case_report['case_id']} — {status}",
                "",
                f"**Category:** `{case_report['category']}`",
                "",
                f"**Query:** {case_report['query']}",
                "",
            ]
        )

        evaluation_report = case_report["evaluation"]

        if evaluation_report is None:
            results = case_report["hybrid_results"]
            top_score = (
                results[0]["rrf_score"]
                if results
                else None
            )

            markdown.extend(
                [
                    "**Expected behavior:** No qualifying results.",
                    "",
                    (
                        "**Top RRF score:** "
                        f"`{top_score:.6f}`"
                        if top_score is not None
                        else "**Top RRF score:** No results"
                    ),
                    "",
                ]
            )
        else:
            precision = evaluation_report["precision_at_k"]
            precision_display = (
                f"`{precision:.3f}`"
                if precision is not None
                else "`N/A` — unjudged results present"
            )

            markdown.extend(
                [
                    (
                        "**Primary hit@5:** "
                        f"`{str(evaluation_report['hit_at_k']).lower()}`"
                    ),
                    "",
                    (
                        "**Primary retrieved count:** "
                        f"`{evaluation_report['primary_retrieved_count']}`"
                    ),
                    "",
                    f"**Precision@5:** {precision_display}",
                    "",
                    (
                        "**Retrieval judgments:** "
                        f"`{evaluation_report['relevant_retrieved_count']} relevant`, "
                        f"`{evaluation_report['nonrelevant_retrieved_count']} "
                        "nonrelevant`, "
                        f"`{evaluation_report['unjudged_retrieved_count']} unjudged`"
                    ),
                    "",
                    (
                        "**Recall@5:** "
                        f"`{evaluation_report['recall_at_k']:.3f}`"
                    ),
                    "",
                    (
                        "**Reciprocal rank:** "
                        f"`{evaluation_report['reciprocal_rank']:.3f}`"
                    ),
                    "",
                ]
            )

        markdown.extend(["#### Hybrid results", ""])
        results = case_report["hybrid_results"]

        if not results:
            markdown.extend(["No results were returned.", ""])
        else:
            for result in results:
                heading = (
                    " > ".join(result["heading_path"])
                    or "(none)"
                )

                markdown.extend(
                    [
                        (
                            f"{result['hybrid_rank']}. "
                            f"**{result['title']}**"
                        ),
                        (
                            "   - Judgment: "
                            f"`{result['judgment']}`"
                        ),
                        (
                            "   - RRF score: "
                            f"`{result['rrf_score']:.6f}`"
                        ),
                        (
                            "   - Vector rank: `"
                            f"{_format_optional_rank(result['vector_rank'])}`"
                        ),
                        (
                            "   - Vector score: `"
                            f"{_format_optional_score(result['vector_score'])}`"
                        ),
                        (
                            "   - BM25 rank: `"
                            f"{_format_optional_rank(result['bm25_rank'])}`"
                        ),
                        (
                            "   - BM25 score: `"
                            f"{_format_optional_score(result['bm25_score'])}`"
                        ),
                        f"   - Heading: {heading}",
                        f"   - Chunk: `{result['chunk_id']}`",
                        f"   - Text: {result['text']}",
                        "",
                    ]
                )

        if case_report["notes"]:
            markdown.extend(
                [
                    (
                        "**Dataset note:** "
                        f"{case_report['notes']}"
                    ),
                    "",
                ]
            )

        markdown.extend(["---", ""])

    MARKDOWN_OUTPUT_PATH.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print(
        "PASS: Hybrid evaluation written to "
        f"{JSON_OUTPUT_PATH} and {MARKDOWN_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
