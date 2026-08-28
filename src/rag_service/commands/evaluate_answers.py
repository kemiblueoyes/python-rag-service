"""Evaluate live answer generation against the gold dataset."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag_service.config import settings
from rag_service.evaluation.answers import (
    AnswerEvaluationResult,
    evaluate_answer_case,
)
from rag_service.evaluation.dataset import load_evaluation_dataset
from rag_service.generation import (
    AnswerGenerator,
    GeneratedAnswer,
    create_answer_generator,
)
from rag_service.generation.models import ContextSource
from rag_service.retrieval import (
    RetrievalRequest,
    RetrievalResult,
    RetrievalService,
    create_retrieval_service,
)

DATASET_PATH = Path("evaluation/datasets/baseline.json")
OUTPUT_DIRECTORY = Path("data/evaluation")
JSON_OUTPUT_PATH = OUTPUT_DIRECTORY / "answer_baseline.json"
MARKDOWN_OUTPUT_PATH = OUTPUT_DIRECTORY / "answer_baseline.md"

EVALUATION_DEPTH = 5


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value * 100:.1f}%"


def _accuracy(values: list[bool]) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)


def _serialize_retrieval_result(
    rank: int,
    result: RetrievalResult,
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


def _serialize_source(
    source: ContextSource,
) -> dict[str, Any]:
    chunk = source.chunk

    return {
        "citation_id": source.citation_id,
        "score": source.score,
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "title": chunk.title,
        "heading_path": chunk.heading_path,
        "url": chunk.url,
        "text": chunk.text,
    }


def _run_case(
    *,
    query: str,
    filters: dict[str, Any],
    retrieval_service: RetrievalService,
    answer_generator: AnswerGenerator,
) -> tuple[list[RetrievalResult], GeneratedAnswer]:
    results = retrieval_service.retrieve(
        RetrievalRequest(
            query=query,
            limit=EVALUATION_DEPTH,
            filters=filters,
        )
    )

    answer = answer_generator.generate(
        question=query,
        results=results,
    )

    return results, answer


def main() -> None:
    """Run live answer evaluation against the gold dataset."""

    if not settings.voyage_api_key:
        raise ValueError("VOYAGE_API_KEY must be configured.")

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY must be configured.")

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
    answer_generator = create_answer_generator(settings)

    evaluations: list[AnswerEvaluationResult] = []
    case_reports: list[dict[str, Any]] = []

    case_passes: list[bool] = []
    sufficiency_checks: list[bool] = []
    citation_checks: list[bool] = []
    answerable_passes: list[bool] = []
    unanswerable_passes: list[bool] = []

    for case in dataset.cases:
        expectation = case.answer

        if expectation is None:
            raise ValueError(
                f"Evaluation case {case.id!r} has no answer expectation."
            )

        results, answer = _run_case(
            query=case.query,
            filters=case.filters,
            retrieval_service=retrieval_service,
            answer_generator=answer_generator,
        )

        evaluation = evaluate_answer_case(
            case,
            answer,
        )

        evaluations.append(evaluation)
        case_passes.append(evaluation.passed)
        sufficiency_checks.append(evaluation.sufficiency_correct)
        citation_checks.append(evaluation.citation_behavior_correct)

        if expectation.expected_sufficient_evidence:
            answerable_passes.append(evaluation.passed)
        else:
            unanswerable_passes.append(evaluation.passed)

        case_reports.append(
            {
                "case_id": case.id,
                "category": case.category,
                "query": case.query,
                "expected_answer": expectation.model_dump(),
                "evaluation": asdict(evaluation),
                "passed": evaluation.passed,
                "generated_answer": answer.answer,
                "retrieved_results": [
                    _serialize_retrieval_result(rank, result)
                    for rank, result in enumerate(
                        results,
                        start=1,
                    )
                ],
                "cited_sources": [
                    _serialize_source(source)
                    for source in answer.sources
                ],
                "notes": case.notes,
            }
        )

    generated_at = datetime.now(UTC).isoformat()

    overall_pass_rate = _accuracy(case_passes)
    sufficiency_accuracy = _accuracy(sufficiency_checks)
    citation_accuracy = _accuracy(citation_checks)
    answerable_pass_rate = _accuracy(answerable_passes)
    unanswerable_pass_rate = _accuracy(unanswerable_passes)

    json_report = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.version,
        "generated_at": generated_at,
        "collection": settings.qdrant_collection,
        "embedding_model": settings.embedding_model,
        "generation_model": settings.generation_model,
        "support_cutoff": settings.retrieval_support_cutoff,
        "retrieval_limit": EVALUATION_DEPTH,
        "summary": {
            "total_cases": len(evaluations),
            "passed_cases": sum(case_passes),
            "failed_cases": len(case_passes) - sum(case_passes),
            "overall_pass_rate": overall_pass_rate,
            "sufficiency_accuracy": sufficiency_accuracy,
            "citation_behavior_accuracy": citation_accuracy,
            "answerable_cases": len(answerable_passes),
            "answerable_pass_rate": answerable_pass_rate,
            "unanswerable_cases": len(unanswerable_passes),
            "unanswerable_pass_rate": unanswerable_pass_rate,
        },
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
        "# Answer Evaluation Baseline",
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
        f"Generation model: `{settings.generation_model}`",
        "",
        (
            "Retrieval support cutoff: "
            f"`{settings.retrieval_support_cutoff:.2f}`"
        ),
        "",
        f"Retrieval results per query: `{EVALUATION_DEPTH}`",
        "",
        "## Summary",
        "",
        f"- Total cases: **{len(evaluations)}**",
        f"- Passed structural checks: **{sum(case_passes)}**",
        (
            "- Structural pass rate: "
            f"**{_format_percentage(overall_pass_rate)}**"
        ),
        (
            "- Evidence-sufficiency accuracy: "
            f"**{_format_percentage(sufficiency_accuracy)}**"
        ),
        (
            "- Citation-behavior accuracy: "
            f"**{_format_percentage(citation_accuracy)}**"
        ),
        (
            "- Answerable-case pass rate: "
            f"**{_format_percentage(answerable_pass_rate)}**"
        ),
        (
            "- Unanswerable-case pass rate: "
            f"**{_format_percentage(unanswerable_pass_rate)}**"
        ),
        "",
        (
            "> Structural PASS/FAIL does not score whether the generated "
            "answer covers the required semantic points. Required points "
            "are included below for qualitative review."
        ),
        "",
        "## Case results",
        "",
    ]

    for case_report in case_reports:
        evaluation = case_report["evaluation"]
        expected_answer = case_report["expected_answer"]
        passed = case_report["passed"]

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
                (
                    "**Expected sufficient evidence:** "
                    f"`{str(expected_answer['expected_sufficient_evidence']).lower()}`"
                ),
                "",
                (
                    "**Actual sufficient evidence:** "
                    f"`{str(evaluation['actual_sufficient_evidence']).lower()}`"
                ),
                "",
                (
                    "**Sufficiency correct:** "
                    f"`{str(evaluation['sufficiency_correct']).lower()}`"
                ),
                "",
                (
                    "**Citation behavior correct:** "
                    f"`{str(evaluation['citation_behavior_correct']).lower()}`"
                ),
                "",
                (
                    "**Primary citation present:** "
                    f"`{str(evaluation['primary_citation_present']).lower()}`"
                ),
                "",
                "#### Required points for qualitative review",
                "",
            ]
        )

        required_points = expected_answer["required_points"]

        if required_points:
            for point in required_points:
                markdown.append(f"- {point}")
        else:
            markdown.append("None.")

        markdown.extend(
            [
                "",
                "#### Generated answer",
                "",
                case_report["generated_answer"],
                "",
                "#### Cited sources",
                "",
            ]
        )

        cited_sources = case_report["cited_sources"]

        if not cited_sources:
            markdown.extend(
                [
                    "No cited sources.",
                    "",
                ]
            )
        else:
            for source in cited_sources:
                heading = (
                    " > ".join(source["heading_path"])
                    or "(none)"
                )

                markdown.extend(
                    [
                        (
                            f"##### [{source['citation_id']}] "
                            f"{source['title']}"
                        ),
                        "",
                        f"**Heading:** {heading}",
                        "",
                        f"**Chunk ID:** `{source['chunk_id']}`",
                        "",
                        f"**Retrieval score:** `{source['score']:.6f}`",
                        "",
                        "**Source text:**",
                        "",
                        source["text"],
                        "",
                    ]
                )

        unacceptable_chunk_ids = evaluation[
            "unacceptable_citation_chunk_ids"
        ]

        if unacceptable_chunk_ids:
            markdown.extend(
                [
                    "**Unacceptable cited chunks:**",
                    "",
                    *[
                        f"- `{chunk_id}`"
                        for chunk_id in unacceptable_chunk_ids
                    ],
                    "",
                ]
            )

        markdown.extend(
            [
                "#### Retrieved context",
                "",
            ]
        )

        retrieved_results = case_report["retrieved_results"]

        if not retrieved_results:
            markdown.extend(
                [
                    "No results passed the retrieval support gate.",
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
        "PASS: Answer evaluation written to "
        f"{JSON_OUTPUT_PATH} and {MARKDOWN_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()