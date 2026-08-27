"""Smoke test live retrieval and grounded answer generation."""

from datetime import UTC, datetime
from pathlib import Path

from rag_service.config import settings
from rag_service.generation import (
    AnswerGenerator,
    GeneratedAnswer,
    create_answer_generator,
)
from rag_service.retrieval import (
    RetrievalRequest,
    RetrievalService,
    create_retrieval_service,
)

SMOKE_QUESTION = (
    "How is the role of technical writer changing?"
)

OUTPUT_PATH = Path(
    "data/answer_generation_smoke_result.md"
)

def run(
    retrieval_service: RetrievalService,
    answer_generator: AnswerGenerator,
) -> GeneratedAnswer:
    """Run the live retrieval and answer-generation workflow."""

    results = retrieval_service.retrieve(
        RetrievalRequest(
            query=SMOKE_QUESTION,
            limit=5,
            filters={"source": "wordpress"},
        )
    )

    if not results:
        raise RuntimeError(
            "Smoke-test retrieval returned no qualifying sources."
        )

    answer = answer_generator.generate(
        question=SMOKE_QUESTION,
        results=results,
    )

    if not answer.sufficient_evidence:
        raise RuntimeError(
            "The model reported insufficient evidence "
            "for the smoke-test question."
        )

    if not answer.sources:
        raise RuntimeError(
            "The generated answer contained no validated sources."
        )

    return answer

def write_report(
    answer: GeneratedAnswer,
    *,
    model: str,
    collection: str,
    support_cutoff: float,
    output_path: Path = OUTPUT_PATH,
) -> Path:
    """Write a reviewable Markdown smoke-test report."""

    report = [
        "# Answer Generation Smoke Test",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        f"Model: `{model}`",
        "",
        f"Qdrant collection: `{collection}`",
        "",
        f"Retrieval support cutoff: `{support_cutoff:.2f}`",
        "",
        "## Question",
        "",
        SMOKE_QUESTION,
        "",
        "## Answer",
        "",
        answer.answer,
        "",
        (
            "**Evidence sufficient:** "
            f"`{str(answer.sufficient_evidence).lower()}`"
        ),
        "",
        "## Validated sources",
        "",
    ]

    for source in answer.sources:
        heading = (
            " > ".join(source.chunk.heading_path)
            or "(none)"
        )

        report.extend(
            [
                (
                    f"### [{source.citation_id}] "
                    f"{source.chunk.title}"
                ),
                "",
                f"**Heading:** {heading}",
                "",
                f"**URL:** {source.chunk.url}",
                "",
                f"**Chunk ID:** `{source.chunk.chunk_id}`",
                "",
                f"**Retrieval score:** `{source.score:.6f}`",
                "",
                "**Source text:**",
                "",
                source.chunk.text,
                "",
            ]
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    return output_path

def main() -> None:
    """Run the smoke test using configured live providers."""

    if not settings.voyage_api_key:
        raise ValueError("VOYAGE_API_KEY must be configured.")

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY must be configured.")

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

    answer = run(
        create_retrieval_service(settings),
        create_answer_generator(settings),
    )

    report_path = write_report(
        answer,
        model=settings.generation_model,
        collection=settings.qdrant_collection,
        support_cutoff=settings.retrieval_support_cutoff,
    )

    print(
        "PASS: Answer-generation smoke-test report "
        f"written to {report_path}"
    )

if __name__ == "__main__":
    main()