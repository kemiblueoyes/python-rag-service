"""Evaluate live retrieval against the gold baseline dataset."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag_service.config import settings
from rag_service.evaluation.dataset import load_evaluation_dataset
from rag_service.evaluation.retrieval import (
    RetrievalEvaluationResult,
    evaluate_retrieval_case,
    summarize_retrieval_evaluations,
)
from rag_service.retrieval import (
    RetrievalRequest,
    create_retrieval_service,
)

DATASET_PATH = Path("evaluation/datasets/baseline.json")
OUTPUT_DIRECTORY = Path("data/evaluation")
JSON_OUTPUT_PATH = OUTPUT_DIRECTORY / "retrieval_baseline.json"
MARKDOWN_OUTPUT_PATH = OUTPUT_DIRECTORY / "retrieval_baseline.md"

EVALUATION_DEPTH = 5


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value * 100:.1f}%"


def _serialize_result(
    rank: int,
    result: Any,
) -> dict[str, Any]:
    chunk = result.chunk

    return {
        "rank": rank,
        "score": result.score,
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "title": chunk.title,
        "heading_path": chunk.heading_path,
        "url": chunk.url,
    }


def _case_passed(
    evaluation: RetrievalEvaluationResult,
) -> bool:
    if evaluation.expected_empty:
        return evaluation.empty_result_correct is True

    return evaluation.hit_at_k


def main() -> None:
    """Run the retrieval baseline against the live index."""

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
    retrieval_service = create_retrieval_service(settings)

    evaluations: list[RetrievalEvaluationResult] = []
    case_reports: list[dict[str, Any]] = []

    for case in dataset.cases:
        results = retrieval_service.retrieve(
            RetrievalRequest(
                query=case.query,
                limit=EVALUATION_DEPTH,
                filters=case.filters,
            )
        )

        evaluation = evaluate_retrieval_case(
            case,
            results,
            k=EVALUATION_DEPTH,
        )

        evaluations.append(evaluation)

        case_reports.append(
            {
                "case_id": case.id,
                "category": case.category,
                "query": case.query,
                "expected_empty": case.retrieval.expect_empty,
                "expected_sources": [
                    source.model_dump()
                    for source in case.retrieval.relevant_sources
                ],
                "evaluation": asdict(evaluation),
                "passed": _case_passed(evaluation),
                "retrieved_results": [
                    _serialize_result(rank, result)
                    for rank, result in enumerate(
                        results,
                        start=1,
                    )
                ],
                "notes": case.notes,
            }
        )

    summary = summarize_retrieval_evaluations(evaluations)

    generated_at = datetime.now(UTC).isoformat()

    json_report = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.version,
        "generated_at": generated_at,
        "collection": settings.qdrant_collection,
        "embedding_model": settings.embedding_model,
        "minimum_retrieval_score": settings.retrieval_min_score,
        "k": EVALUATION_DEPTH,
        "summary": asdict(summary),
        "cases": case_reports,
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
        "# Retrieval Evaluation Baseline",
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
        (
            "Minimum retrieval score: "
            f"`{settings.retrieval_min_score:.2f}`"
        ),
        "",
        f"Results evaluated per query: `{EVALUATION_DEPTH}`",
        "",
        "## Summary",
        "",
        f"- Total cases: **{summary.total_cases}**",
        f"- Answerable cases: **{summary.answerable_cases}**",
        f"- Unanswerable cases: **{summary.unanswerable_cases}**",
        (
            "- Primary hit rate@5: "
            f"**{_format_percentage(summary.hit_rate_at_k)}**"
        ),
        (
            "- Mean precision@5: "
            f"**{_format_percentage(summary.mean_precision_at_k)}**"
        ),
        (
            "- Precision-evaluable answerable cases: "
            f"**{summary.precision_evaluable_cases}"
            f"/{summary.answerable_cases}**"
        ),
        (
            "- Mean recall@5: "
            f"**{_format_percentage(summary.mean_recall_at_k)}**"
        ),
        (
            "- Mean reciprocal rank: "
            f"**{summary.mean_reciprocal_rank:.3f}**"
        ),
        (
            "- Unanswerable accuracy: " # maps to empty_result_correct
            f"**{_format_percentage(summary.unanswerable_accuracy)}**"
        ),
        (
            "- Overall success rate: "
            f"**{_format_percentage(summary.overall_success_rate)}**"
        ),
        "",
        "## Case results",
        "",
    ]

    for case_report in case_reports:
        evaluation = case_report["evaluation"]
        passed = case_report["passed"]

        precision = evaluation["precision_at_k"]

        precision_display = (
            f"`{precision:.3f}`"
            if precision is not None
            else "`N/A` — unjudged results present"
        )

        markdown.extend(
            [
                (
                    f"### {case_report['case_id']} — "
                    f"{'PASS' if passed else 'FAIL'}"
                ),
                "",
                f"**Category:** `{case_report['category']}`",
                "",
                f"**Query:** {case_report['query']}",
                "",
            ]
        )

        if case_report["expected_empty"]:
            markdown.extend(
                [
                    "**Expected behavior:** No qualifying results.",
                    "",
                    (
                        "**Empty-result correct:** "
                        f"`{str(evaluation['empty_result_correct']).lower()}`"
                    ),
                    "",
                ]
            )
        else:
            markdown.extend(
                [
                    (
                        "**Primary hit@5:** "
                        f"`{str(evaluation['hit_at_k']).lower()}`"
                    ),
                    "",
                    f"**Precision@5:** {precision_display}",
                    "",
                    (
                        "**Retrieval judgments:** "
                        f"`{evaluation['relevant_retrieved_count']} relevant`, "
                        f"`{evaluation['nonrelevant_retrieved_count']} nonrelevant`, "
                        f"`{evaluation['unjudged_retrieved_count']} unjudged`"
                    ),
                    "",
                    (
                        "**Recall@5:** "
                        f"`{evaluation['recall_at_k']:.3f}`"
                    ),
                    "",
                    (
                        "**Reciprocal rank:** "
                        f"`{evaluation['reciprocal_rank']:.3f}`"
                    ),
                    "",
                ]
            )

        markdown.extend(
            [
                "#### Retrieved results",
                "",
            ]
        )

        retrieved_results = case_report["retrieved_results"]

        if not retrieved_results:
            markdown.extend(
                [
                    "No results met the retrieval threshold.",
                    "",
                ]
            )
        else:
            for result in retrieved_results:
                heading = (
                    " > ".join(result["heading_path"])
                    or "(none)"
                )

                markdown.extend(
                    [
                        (
                            f"{result['rank']}. "
                            f"**{result['title']}** "
                            f"— `{result['score']:.6f}`"
                        ),
                        f"   - Heading: {heading}",
                        f"   - Chunk: `{result['chunk_id']}`",
                        "",
                    ]
                )

        if case_report["notes"]:
            markdown.extend(
                [
                    f"**Dataset note:** {case_report['notes']}",
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
        "PASS: Retrieval evaluation written to "
        f"{JSON_OUTPUT_PATH} and {MARKDOWN_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()