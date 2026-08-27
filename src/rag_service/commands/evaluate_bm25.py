"""Evaluate BM25 lexical retrieval against the gold retrieval dataset.

This experiment:
- Builds a temporary BM25 index from the chunks currently stored in Qdrant.
- Indexes title, heading path, and chunk text.
- Runs the same evaluation queries used by the semantic baseline.
- Keeps the top five BM25 results after applying each case's metadata filters.
- Records BM25 scores and retrieval judgments.
- Does not apply or invent a BM25 score cutoff.
- Labels expected-empty cases CUTOFF NOT EVALUATED.
"""

import json
from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import bm25s  # type: ignore[import-untyped]
from qdrant_client import QdrantClient

from rag_service.config import settings
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

DATASET_PATH = Path("evaluation/datasets/baseline.json")
OUTPUT_DIRECTORY = Path("data/evaluation")
JSON_OUTPUT_PATH = OUTPUT_DIRECTORY / "bm25_evaluation.json"
MARKDOWN_OUTPUT_PATH = OUTPUT_DIRECTORY / "bm25_evaluation.md"

EVALUATION_DEPTH = 5
SCROLL_BATCH_SIZE = 256


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value * 100:.1f}%"


def _document_for_bm25(chunk: DocumentChunk) -> str:
    heading = " > ".join(chunk.heading_path)

    parts = [
        chunk.title,
        heading,
        chunk.text,
    ]

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

            chunk = DocumentChunk.model_validate(
                dict(point.payload)
            )

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
                f"Unsupported BM25 evaluation filter: {key}"
            )

        actual = getattr(chunk, key)

        if isinstance(expected, str):
            if actual != expected:
                return False
            continue

        if actual not in expected:
            return False

    return True


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
    """Run the BM25 experiment across the evaluation dataset."""

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
    chunks = _load_chunks()

    corpus = [
        _document_for_bm25(chunk)
        for chunk in chunks
    ]

    corpus_tokens = bm25s.tokenize(
        corpus,
        stopwords="en",
    )

    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)

    answerable_evaluations: list[
        RetrievalEvaluationResult
    ] = []
    case_reports: list[dict[str, Any]] = []
    passed_answerable_count = 0

    for case in dataset.cases:
        query_tokens = bm25s.tokenize(
            [case.query],
            stopwords="en",
        )

        document_ids, scores = retriever.retrieve(
            query_tokens,
            k=len(chunks),
        )

        bm25_results: list[RetrievalResult] = []
        serialized_results: list[dict[str, Any]] = []

        for position in range(document_ids.shape[1]):
            chunk_index = int(document_ids[0, position])
            chunk = chunks[chunk_index]

            if not _matches_filters(chunk, case.filters):
                continue

            score = float(scores[0, position])

            bm25_results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=score,
                )
            )

            serialized_results.append(
                {
                    "bm25_rank": len(bm25_results),
                    "bm25_score": score,
                    "judgment": _judgment_for_chunk(
                        case,
                        chunk,
                    ),
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "title": chunk.title,
                    "heading_path": chunk.heading_path,
                    "url": chunk.url,
                    "text": chunk.text,
                }
            )

            if len(bm25_results) >= EVALUATION_DEPTH:
                break

        evaluation: RetrievalEvaluationResult | None
        passed: bool | None

        if case.retrieval.expect_empty:
            evaluation = None
            passed = None
        else:
            evaluation = evaluate_retrieval_case(
                case,
                bm25_results,
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
                "bm25_results": serialized_results,
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
        "corpus_size": len(chunks),
        "indexed_fields": [
            "title",
            "heading_path",
            "text",
        ],
        "evaluation_depth": EVALUATION_DEPTH,
        "bm25_score_cutoff": None,
        "summary": summary,
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
        "# BM25 Retrieval Evaluation",
        "",
        f"Generated: {generated_at}",
        "",
        f"Dataset: `{dataset.dataset_id}`",
        "",
        f"Dataset version: `{dataset.version}`",
        "",
        f"Collection: `{settings.qdrant_collection}`",
        "",
        f"Indexed chunks: `{len(chunks)}`",
        "",
        (
            "Indexed fields: `title`, `heading_path`, "
            "`text`"
        ),
        "",
        f"Results evaluated per query: `{EVALUATION_DEPTH}`",
        "",
        "**BM25 score cutoff:** Not applied",
        "",
        (
            "Expected-empty cases are not marked pass or fail "
            "yet because no BM25 score cutoff has been chosen."
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
            results = case_report["bm25_results"]

            top_score = (
                results[0]["bm25_score"]
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
                        "**Top BM25 score:** "
                        f"`{top_score:.6f}`"
                        if top_score is not None
                        else "**Top BM25 score:** No results"
                    ),
                    "",
                ]
            )
        else:
            precision = evaluation_report[
                "precision_at_k"
            ]

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

        markdown.extend(
            [
                "#### BM25 results",
                "",
            ]
        )

        results = case_report["bm25_results"]

        if not results:
            markdown.extend(
                [
                    "No results were returned.",
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
                            f"{result['bm25_rank']}. "
                            f"**{result['title']}**"
                        ),
                        (
                            "   - Judgment: "
                            f"`{result['judgment']}`"
                        ),
                        (
                            "   - BM25 score: "
                            f"`{result['bm25_score']:.6f}`"
                        ),
                        f"   - Heading: {heading}",
                        (
                            "   - Chunk: "
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
        "PASS: BM25 evaluation written to "
        f"{JSON_OUTPUT_PATH} and {MARKDOWN_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
