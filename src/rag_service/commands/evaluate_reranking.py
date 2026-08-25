"""Evaluate reranking against the gold retrieval dataset:
Retrieves 20 candidates without the current 0.50 cutoff.
Reranks those 20 and keeps the best 5.
Shows both the old vector score/rank and the new rerank score/rank.
Includes the chunk text.
Does not invent a rerank cutoff.
The three unanswerable cases are therefore labeled CUTOFF NOT EVALUATED, not failed.
"""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

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
from rag_service.retrieval.models import RetrievalResult
from rag_service.vectorstores import create_vector_store
from rag_service.vectorstores.base import SearchResult

DATASET_PATH = Path("evaluation/datasets/baseline.json")
OUTPUT_DIRECTORY = Path("data/evaluation")
JSON_OUTPUT_PATH = OUTPUT_DIRECTORY / "reranking_evaluation.json"
MARKDOWN_OUTPUT_PATH = OUTPUT_DIRECTORY / "reranking_evaluation.md"

CANDIDATE_DEPTH = 20
EVALUATION_DEPTH = 5
RERANK_MODEL = "rerank-2.5"

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


def _deduplicate_candidates(
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


def _document_for_reranking(result: SearchResult) -> str:
    heading = " > ".join(result.chunk.heading_path) or "(none)"

    return (
        f"Title: {result.chunk.title}\n"
        f"Heading: {heading}\n"
        f"Content:\n{result.chunk.text}"
    )


def _matches_source(
    result: SearchResult,
    source: GoldSource | NonRelevantSource,
) -> bool:
    chunk = result.chunk

    if source.chunk_id is not None:
        return chunk.chunk_id == source.chunk_id

    return (
        chunk.document_id == source.document_id
        and chunk.heading_path == source.heading_path
    )


def _judgment_for_result(
    case: EvaluationCase,
    result: SearchResult,
) -> str:
    for relevant_source in case.retrieval.relevant_sources:
        if _matches_source(result, relevant_source):
            return f"relevant ({relevant_source.role})"

    for nonrelevant_source in case.retrieval.nonrelevant_sources:
        if _matches_source(result, nonrelevant_source):
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

        return (
            evaluation.primary_retrieved_count
            == required_primary_count
        )

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
        "answerable_success_rate": (
            passed_count / len(evaluations)
        ),
        "primary_hit_rate_at_5": (
            sum(
                evaluation.hit_at_k
                for evaluation in evaluations
            )
            / len(evaluations)
        ),
        "mean_precision_at_5": (
            sum(precision_values) / len(precision_values)
            if precision_values
            else None
        ),
        "precision_evaluable_cases": len(precision_values),
        "mean_recall_at_5": (
            sum(
                evaluation.recall_at_k
                for evaluation in evaluations
            )
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
    """Run the reranking experiment across the evaluation dataset."""

    if not settings.voyage_api_key:
        raise ValueError("VOYAGE_API_KEY must be configured.")

    if (
        not settings.qdrant_api_key
        and not settings.qdrant_url.startswith(
            "http://localhost"
        )
    ):
        raise ValueError(
            "QDRANT_API_KEY must be configured when using "
            "a remote Qdrant instance."
        )

    dataset = load_evaluation_dataset(DATASET_PATH)

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

    for case in dataset.cases:
        query_vector = embedding_provider.embed_query(
            case.query
        )

        candidates = vector_store.search(
            query_vector=query_vector,
            limit=CANDIDATE_DEPTH,
            filters=case.filters or None,
        )

        candidates = _deduplicate_candidates(candidates)

        reranked_results: list[RetrievalResult] = []
        serialized_results: list[dict[str, Any]] = []

        if candidates:
            documents = [
                _document_for_reranking(candidate)
                for candidate in candidates
            ]

            response = rerank_client.rerank(
                case.query,
                documents,
                model=RERANK_MODEL,
                top_k=min(
                    EVALUATION_DEPTH,
                    len(candidates),
                ),
            )

            for rerank_rank, reranked in enumerate(
                response.results,
                start=1,
            ):
                if (
                    reranked.index < 0
                    or reranked.index >= len(candidates)
                ):
                    raise RuntimeError(
                        "Voyage returned an invalid "
                        "candidate index."
                    )

                candidate = candidates[reranked.index]
                rerank_score = float(
                    reranked.relevance_score
                )

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
                        "vector_rank": (
                            reranked.index + 1
                        ),
                        "vector_score": candidate.score,
                        "judgment": (
                            _judgment_for_result(
                                case,
                                candidate,
                            )
                        ),
                        "chunk_id": (
                            candidate.chunk.chunk_id
                        ),
                        "document_id": (
                            candidate.chunk.document_id
                        ),
                        "title": candidate.chunk.title,
                        "heading_path": (
                            candidate.chunk.heading_path
                        ),
                        "url": candidate.chunk.url,
                        "text": candidate.chunk.text,
                    }
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

            passed = _case_passed(
                case,
                evaluation,
            )

            answerable_evaluations.append(evaluation)

            if passed:
                passed_answerable_count += 1

        case_reports.append(
            {
                "case_id": case.id,
                "category": case.category,
                "query": case.query,
                "expected_empty": (
                    case.retrieval.expect_empty
                ),
                "evaluation": (
                    asdict(evaluation)
                    if evaluation is not None
                    else None
                ),
                "passed": passed,
                "reranked_results": serialized_results,
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
        "rerank_model": RERANK_MODEL,
        "candidate_depth": CANDIDATE_DEPTH,
        "evaluation_depth": EVALUATION_DEPTH,
        "rerank_score_cutoff": None,
        "summary": summary,
        "cases": case_reports
    }

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    JSON_OUTPUT_PATH.write_text(
        json.dumps(
            json_report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    markdown: list[str] = [
        "# Reranking Evaluation",
        "",
        f"Generated: {generated_at}",
        "",
        f"Dataset: `{dataset.dataset_id}`",
        "",
        f"Dataset version: `{dataset.version}`",
        "",
        f"Embedding model: `{settings.embedding_model}`",
        "",
        f"Reranking model: `{RERANK_MODEL}`",
        "",
        f"Vector candidates per query: `{CANDIDATE_DEPTH}`",
        "",
        f"Reranked results evaluated: `{EVALUATION_DEPTH}`",
        "",
        "**Rerank score cutoff:** Not applied",
        "",
        (
            "Unanswerable cases are not marked pass or fail "
            "yet because no rerank score cutoff has been chosen."
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
                (
                    f"### {case_report['case_id']} "
                    f"— {status}"
                ),
                "",
                f"**Category:** `{case_report['category']}`",
                "",
                f"**Query:** {case_report['query']}",
                "",
            ]
        )

        evaluation_report = case_report["evaluation"]

        if evaluation_report is None:
            results = case_report["reranked_results"]

            top_score = (
                results[0]["rerank_score"]
                if results
                else None
            )

            markdown.extend(
                [
                    (
                        "**Expected behavior:** "
                        "No qualifying results."
                    ),
                    "",
                    (
                        "**Top rerank score:** "
                        f"`{top_score:.6f}`"
                        if top_score is not None
                        else "**Top rerank score:** No results"
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
                        f"`{evaluation_report['nonrelevant_retrieved_count']}"
                        " nonrelevant`, "
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

        markdown.extend(
            [
                "#### Reranked results",
                "",
            ]
        )

        results = case_report["reranked_results"]

        if not results:
            markdown.extend(
                [
                    "No vector candidates were returned.",
                    "",
                ]
            )
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
                            "   - Original vector rank: "
                            f"`{result['vector_rank']}`"
                        ),
                        (
                            "   - Vector score: "
                            f"`{result['vector_score']:.6f}`"
                        ),
                        f"   - Heading: {heading}",
                        (
                            f"   - Chunk: "
                            f"`{result['chunk_id']}`"
                        ),
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

        markdown.extend(
            [
                "---",
                "",
            ]
        )

    MARKDOWN_OUTPUT_PATH.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print(
        "PASS: Reranking evaluation written to "
        f"{JSON_OUTPUT_PATH} and "
        f"{MARKDOWN_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()