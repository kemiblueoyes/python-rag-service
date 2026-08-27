"""Evaluate hybrid retrieval, Voyage reranking, and a support gate.

This experiment:
- Retrieves 20 semantic candidates without the current 0.50 cutoff.
- Retrieves 20 BM25 candidates from the full Qdrant chunk corpus.
- Combines both ranked lists with Reciprocal Rank Fusion (RRF).
- Sends the top 20 fused candidates to Voyage reranking.
- Evaluates the raw top five reranked results against the gold dataset.
- Applies a provisional 0.70 query-level support gate after reranking.
- Keeps raw reranked results in the report for failure analysis.
- Records vector, BM25, RRF, and rerank ranks/scores.
"""

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

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
JSON_OUTPUT_PATH = OUTPUT_DIRECTORY / "hybrid_reranking_evaluation.json"
MARKDOWN_OUTPUT_PATH = OUTPUT_DIRECTORY / "hybrid_reranking_evaluation.md"

VECTOR_CANDIDATE_DEPTH = 20
BM25_CANDIDATE_DEPTH = 20
RERANK_CANDIDATE_DEPTH = 20
EVALUATION_DEPTH = 5
RRF_K = 60
RERANK_MODEL = "rerank-2.5"
RERANK_SCORE_CUTOFF = 0.70
SCROLL_BATCH_SIZE = 256


@dataclass
class _HybridCandidate:
    chunk: DocumentChunk
    vector_rank: int | None = None
    vector_score: float | None = None
    bm25_rank: int | None = None
    bm25_score: float | None = None
    rrf_score: float = 0.0


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


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value * 100:.1f}%"


def _format_optional_rank(value: int | None) -> str:
    return str(value) if value is not None else "—"


def _format_optional_score(value: float | None) -> str:
    return f"{value:.6f}" if value is not None else "—"


def _document_for_bm25(chunk: DocumentChunk) -> str:
    heading = " > ".join(chunk.heading_path)
    parts = [chunk.title, heading, chunk.text]

    return "\n".join(part for part in parts if part)


def _document_for_reranking(candidate: _HybridCandidate) -> str:
    heading = " > ".join(candidate.chunk.heading_path) or "(none)"

    return (
        f"Title: {candidate.chunk.title}\n"
        f"Heading: {heading}\n"
        f"Content:\n{candidate.chunk.text}"
    )


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

        if len(results) >= BM25_CANDIDATE_DEPTH:
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
                else VECTOR_CANDIDATE_DEPTH + 1
            ),
            -(
                candidate.bm25_rank
                if candidate.bm25_rank is not None
                else BM25_CANDIDATE_DEPTH + 1
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


def _top_rerank_score(
    results: list[RetrievalResult],
) -> float | None:
    if not results:
        return None

    return results[0].score


def _support_gate_accepts(
    results: list[RetrievalResult],
) -> bool:
    top_score = _top_rerank_score(results)

    return (
        top_score is not None
        and top_score >= RERANK_SCORE_CUTOFF
    )


def _summarize_support_gate(
    case_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    answerable = [
        report
        for report in case_reports
        if not report["expected_empty"]
    ]
    expected_empty = [
        report
        for report in case_reports
        if report["expected_empty"]
    ]

    accepted_answerable = sum(
        report["gate_accepted"] is True
        for report in answerable
    )
    rejected_expected_empty = sum(
        report["gate_accepted"] is False
        for report in expected_empty
    )

    false_positive_case_ids = [
        report["case_id"]
        for report in expected_empty
        if report["gate_accepted"] is True
    ]
    false_negative_case_ids = [
        report["case_id"]
        for report in answerable
        if report["gate_accepted"] is False
    ]

    correct_count = (
        accepted_answerable
        + rejected_expected_empty
    )

    return {
        "total_cases": len(case_reports),
        "correct_cases": correct_count,
        "overall_accuracy": (
            correct_count / len(case_reports)
            if case_reports
            else 0.0
        ),
        "answerable_cases": len(answerable),
        "accepted_answerable_cases": accepted_answerable,
        "answerable_acceptance_rate": (
            accepted_answerable / len(answerable)
            if answerable
            else 0.0
        ),
        "expected_empty_cases": len(expected_empty),
        "rejected_expected_empty_cases": rejected_expected_empty,
        "expected_empty_rejection_rate": (
            rejected_expected_empty / len(expected_empty)
            if expected_empty
            else 0.0
        ),
        "false_positive_case_ids": false_positive_case_ids,
        "false_negative_case_ids": false_negative_case_ids,
    }


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


def main() -> None:
    """Run hybrid retrieval followed by Voyage reranking."""

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

    from voyageai.client import Client

    rerank_client = cast(
        _VoyageRerankClient,
        Client(api_key=settings.voyage_api_key),
    )

    answerable_evaluations: list[
        RetrievalEvaluationResult
    ] = []
    case_reports: list[dict[str, Any]] = []
    passed_answerable_count = 0
    total_rerank_tokens = 0

    for case in dataset.cases:
        query_vector = embedding_provider.embed_query(case.query)

        vector_candidates = vector_store.search(
            query_vector=query_vector,
            limit=VECTOR_CANDIDATE_DEPTH,
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
        rerank_candidates = fused_candidates[:RERANK_CANDIDATE_DEPTH]

        reranked_results: list[RetrievalResult] = []
        serialized_results: list[dict[str, Any]] = []
        rerank_tokens = 0

        if rerank_candidates:
            documents = [
                _document_for_reranking(candidate)
                for candidate in rerank_candidates
            ]

            response = rerank_client.rerank(
                case.query,
                documents,
                model=RERANK_MODEL,
                top_k=min(
                    EVALUATION_DEPTH,
                    len(rerank_candidates),
                ),
            )

            rerank_tokens = response.total_tokens
            total_rerank_tokens += rerank_tokens

            for rerank_rank, reranked in enumerate(
                response.results,
                start=1,
            ):
                if (
                    reranked.index < 0
                    or reranked.index >= len(rerank_candidates)
                ):
                    raise RuntimeError(
                        "Voyage returned an invalid candidate index."
                    )

                candidate = rerank_candidates[reranked.index]
                rerank_score = float(reranked.relevance_score)

                reranked_results.append(
                    RetrievalResult(
                        chunk=candidate.chunk,
                        score=rerank_score,
                    )
                )

                serialized_results.append(
                    {
                        "rerank_rank": rerank_rank,
                        "rerank_score": rerank_score,
                        "hybrid_rank": reranked.index + 1,
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
                )

        top_rerank_score = _top_rerank_score(
            reranked_results
        )
        gate_accepted = _support_gate_accepts(
            reranked_results
        )
        gate_correct = (
            not gate_accepted
            if case.retrieval.expect_empty
            else gate_accepted
        )
        qualifying_result_count = (
            len(reranked_results)
            if gate_accepted
            else 0
        )

        evaluation: RetrievalEvaluationResult | None
        passed: bool | None

        if case.retrieval.expect_empty:
            evaluation = None
            passed = None
        else:
            evaluation = evaluate_retrieval_case(
                case,
                reranked_results,
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
                "top_rerank_score": top_rerank_score,
                "gate_accepted": gate_accepted,
                "gate_correct": gate_correct,
                "qualifying_result_count": (
                    qualifying_result_count
                ),
                "rerank_tokens": rerank_tokens,
                "reranked_results": serialized_results,
                "notes": case.notes,
            }
        )

    summary = _summarize_answerable(
        answerable_evaluations,
        passed_answerable_count,
    )
    support_gate_summary = _summarize_support_gate(
        case_reports
    )
    gate_accuracy = _format_percentage(
        support_gate_summary["overall_accuracy"]
    )
    answerable_acceptance = _format_percentage(
        support_gate_summary["answerable_acceptance_rate"]
    )
    expected_empty_rejection = _format_percentage(
        support_gate_summary["expected_empty_rejection_rate"]
    )
    generated_at = datetime.now(UTC).isoformat()

    json_report = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.version,
        "generated_at": generated_at,
        "collection": settings.qdrant_collection,
        "embedding_model": settings.embedding_model,
        "rerank_model": RERANK_MODEL,
        "corpus_size": len(chunks),
        "vector_candidate_depth": VECTOR_CANDIDATE_DEPTH,
        "bm25_candidate_depth": BM25_CANDIDATE_DEPTH,
        "fusion_method": "reciprocal_rank_fusion",
        "rrf_k": RRF_K,
        "rerank_candidate_depth": RERANK_CANDIDATE_DEPTH,
        "evaluation_depth": EVALUATION_DEPTH,
        "rerank_score_cutoff": RERANK_SCORE_CUTOFF,
        "total_rerank_tokens": total_rerank_tokens,
        "summary": summary,
        "support_gate_summary": support_gate_summary,
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
        "# Hybrid Retrieval + Reranking Evaluation",
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
        f"Reranking model: `{RERANK_MODEL}`",
        "",
        f"Indexed chunks: `{len(chunks)}`",
        "",
        (
            "Vector candidates per query: "
            f"`{VECTOR_CANDIDATE_DEPTH}`"
        ),
        "",
        (
            "BM25 candidates per query: "
            f"`{BM25_CANDIDATE_DEPTH}`"
        ),
        "",
        "Fusion method: `Reciprocal Rank Fusion (RRF)`",
        "",
        f"RRF constant: `{RRF_K}`",
        "",
        (
            "Fused candidates sent to reranker: "
            f"`{RERANK_CANDIDATE_DEPTH}`"
        ),
        "",
        f"Reranked results evaluated: `{EVALUATION_DEPTH}`",
        "",
        f"Total rerank tokens: `{total_rerank_tokens}`",
        "",
        (
            "**Provisional support-gate cutoff:** "
            f"`{RERANK_SCORE_CUTOFF:.2f}`"
        ),
        "",
        (
            "The cutoff is applied at the query level after "
            "reranking. If the top rerank score is below the "
            "cutoff, the query has no qualifying results."
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
        "## Support-gate summary",
        "",
        (
            "- Total cases: "
            f"**{support_gate_summary['total_cases']}**"
        ),
        (
            "- Correct gate decisions: "
            f"**{support_gate_summary['correct_cases']}"
            f"/{support_gate_summary['total_cases']}**"
        ),
        f"- Overall gate accuracy: **{gate_accuracy}**",
        (
            "- Answerable queries accepted: "
            f"**{support_gate_summary['accepted_answerable_cases']}"
            f"/{support_gate_summary['answerable_cases']}**"
        ),
        (
            "- Answerable acceptance rate: "
            f"**{answerable_acceptance}**"
        ),
        (
            "- Expected-empty queries rejected: "
            f"**{support_gate_summary['rejected_expected_empty_cases']}"
            f"/{support_gate_summary['expected_empty_cases']}**"
        ),
        (
            "- Expected-empty rejection rate: "
            f"**{expected_empty_rejection}**"
        ),
        (
            "- False positives: "
            f"**{len(support_gate_summary['false_positive_case_ids'])}**"
        ),
        (
            "- False negatives: "
            f"**{len(support_gate_summary['false_negative_case_ids'])}**"
        ),
        "",
        "## Case results",
        "",
    ]

    for case_report in case_reports:
        passed = case_report["passed"]

        if case_report["expected_empty"]:
            status = (
                "PASS"
                if case_report["gate_correct"]
                else "FAIL"
            )
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
                (
                    "**Rerank tokens:** "
                    f"`{case_report['rerank_tokens']}`"
                ),
                "",
                (
                    "**Top rerank score:** "
                    f"`{case_report['top_rerank_score']:.6f}`"
                    if case_report["top_rerank_score"] is not None
                    else "**Top rerank score:** No results"
                ),
                "",
                (
                    "**Support-gate decision:** "
                    f"`{'ACCEPT' if case_report['gate_accepted'] else 'REJECT'}`"
                ),
                "",
                (
                    "**Support-gate result:** "
                    f"`{'PASS' if case_report['gate_correct'] else 'FAIL'}`"
                ),
                "",
                (
                    "**Qualifying results after gate:** "
                    f"`{case_report['qualifying_result_count']}`"
                ),
                "",
            ]
        )

        evaluation_report = case_report["evaluation"]

        if evaluation_report is None:
            markdown.extend(
                [
                    "**Expected behavior:** No qualifying results.",
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

        markdown.extend(["#### Raw reranked hybrid results", ""])
        results = case_report["reranked_results"]

        if not results:
            markdown.extend(["No fused candidates were returned.", ""])
        else:
            for result in results:
                heading = (
                    " > ".join(result["heading_path"])
                    or "(none)"
                )

                markdown.extend(
                    [
                        (
                            f"{result['rerank_rank']}. "
                            f"**{result['title']}**"
                        ),
                        (
                            "   - Judgment: "
                            f"`{result['judgment']}`"
                        ),
                        (
                            "   - Rerank score: "
                            f"`{result['rerank_score']:.6f}`"
                        ),
                        (
                            "   - Hybrid rank: `"
                            f"{result['hybrid_rank']}`"
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
        "PASS: Hybrid reranking evaluation written to "
        f"{JSON_OUTPUT_PATH} and {MARKDOWN_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
