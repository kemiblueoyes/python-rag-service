"""Evaluate live retrieval against the gold baseline dataset."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag_service.client_lifecycle import close_client
from rag_service.config import settings
from rag_service.evaluation.dataset import load_evaluation_dataset
from rag_service.evaluation.models import EvaluationCase
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
OUTPUT_DIRECTORY = Path("data/evaluation/latest")
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
        "text": chunk.text,
    }


def _case_passed(
    case: EvaluationCase,
    evaluation: RetrievalEvaluationResult,
) -> bool:
    if evaluation.expected_empty:
        return evaluation.empty_result_correct is True

    if case.category == "multi_section":
        required_primary_count = sum(
            source.role == "primary" for source in case.retrieval.relevant_sources
        )

        return evaluation.primary_retrieved_count == required_primary_count

    return evaluation.hit_at_k


def run(
    dataset_path: Path,
    json_output_path: Path,
    markdown_output_path: Path,
) -> dict[str, Any]:
    """Evaluate a fresh retrieval service and return this run's report."""

    if not settings.voyage_api_key:
        raise ValueError("VOYAGE_API_KEY must be configured.")

    if not settings.qdrant_api_key and not settings.qdrant_url.startswith(
        "http://localhost"
    ):
        raise ValueError(
            "QDRANT_API_KEY must be configured when using a remote Qdrant instance."
        )

    dataset = load_evaluation_dataset(dataset_path)
    retrieval_service = create_retrieval_service(settings)

    try:
        evaluations: list[RetrievalEvaluationResult] = []
        case_reports: list[dict[str, Any]] = []
        case_passes: list[bool] = []

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

            passed = _case_passed(
                case,
                evaluation,
            )
            case_passes.append(passed)

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
                    "passed": passed,
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

        overall_success_rate = sum(case_passes) / len(case_passes)

        summary = summarize_retrieval_evaluations(evaluations)

        generated_at = datetime.now(UTC).isoformat()

        json_report = {
            "dataset_id": dataset.dataset_id,
            "dataset_version": dataset.version,
            "generated_at": generated_at,
            "collection": settings.qdrant_collection,
            "embedding_model": settings.embedding_model,
            "support_cutoff": settings.retrieval_support_cutoff,
            "k": EVALUATION_DEPTH,
            "summary": {
                **asdict(summary),
                "overall_success_rate": overall_success_rate,
            },
            "cases": case_reports,
        }

        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_output_path.parent.mkdir(parents=True, exist_ok=True)

        json_output_path.write_text(
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
            (f"Support cutoff: `{settings.retrieval_support_cutoff:.2f}`"),
            "",
            f"Results evaluated per query: `{EVALUATION_DEPTH}`",
            "",
            "## Summary",
            "",
            f"- Total cases: **{summary.total_cases}**",
            f"- Answerable cases: **{summary.answerable_cases}**",
            f"- Unanswerable cases: **{summary.unanswerable_cases}**",
            (f"- Primary hit rate@5: **{_format_percentage(summary.hit_rate_at_k)}**"),
            (
                "- Mean precision@5: "
                f"**{_format_percentage(summary.mean_precision_at_k)}**"
            ),
            (
                "- Precision-evaluable answerable cases: "
                f"**{summary.precision_evaluable_cases}"
                f"/{summary.answerable_cases}**"
            ),
            (f"- Mean recall@5: **{_format_percentage(summary.mean_recall_at_k)}**"),
            (f"- Mean reciprocal rank: **{summary.mean_reciprocal_rank:.3f}**"),
            (
                "- Unanswerable accuracy: "  # maps to empty_result_correct
                f"**{_format_percentage(summary.unanswerable_accuracy)}**"
            ),
            (f"- Overall success rate: **{_format_percentage(overall_success_rate)}**"),
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
                    (f"### {case_report['case_id']} — {'PASS' if passed else 'FAIL'}"),
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
                        (f"**Primary hit@5:** `{str(evaluation['hit_at_k']).lower()}`"),
                        "",
                        (
                            "**Primary retrieved count:** "
                            f"`{evaluation['primary_retrieved_count']}`"
                        ),
                        "",
                        f"**Precision@5:** {precision_display}",
                        "",
                        (
                            "**Retrieval judgments:** "
                            f"`{evaluation['relevant_retrieved_count']} relevant`, "
                            f"`{evaluation['nonrelevant_retrieved_count']} "
                            "nonrelevant`, "
                            f"`{evaluation['unjudged_retrieved_count']} unjudged`"
                        ),
                        "",
                        (f"**Recall@5:** `{evaluation['recall_at_k']:.3f}`"),
                        "",
                        (f"**Reciprocal rank:** `{evaluation['reciprocal_rank']:.3f}`"),
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
                        "No results passed the support cutoff.",
                        "",
                    ]
                )
            else:
                for result in retrieved_results:
                    heading = " > ".join(result["heading_path"]) or "(none)"

                    markdown.extend(
                        [
                            (
                                f"{result['rank']}. "
                                f"**{result['title']}** "
                                f"— `{result['score']:.6f}`"
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

        markdown_output_path.write_text(
            "\n".join(markdown),
            encoding="utf-8",
        )
        return json_report
    finally:
        close_client(retrieval_service, operation="evaluate_retrieval")


def main() -> None:
    """Run the retrieval baseline using the existing CLI defaults."""
    run(DATASET_PATH, JSON_OUTPUT_PATH, MARKDOWN_OUTPUT_PATH)

    print(
        "PASS: Retrieval evaluation written to "
        f"{JSON_OUTPUT_PATH} and {MARKDOWN_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
