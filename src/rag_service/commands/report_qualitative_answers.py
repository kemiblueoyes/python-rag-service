"""Write the human qualitative answer-evaluation report."""

from pathlib import Path

from rag_service.evaluation.qualitative import (
    load_qualitative_answer_review,
    summarize_qualitative_reviews,
    validate_review_against_answer_baseline,
)

REVIEW_PATH = Path(
    "data/evaluation/answer_qualitative_review.json"
)
ANSWER_BASELINE_PATH = Path(
    "data/evaluation/answer_baseline.json"
)
OUTPUT_PATH = Path(
    "data/evaluation/answer_qualitative_review.md"
)


def _format_percentage(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> None:
    """Validate and write the qualitative answer report."""

    review_set = load_qualitative_answer_review(
        REVIEW_PATH
    )

    validate_review_against_answer_baseline(
        review_set,
        ANSWER_BASELINE_PATH,
    )

    summary = summarize_qualitative_reviews(
        review_set
    )

    markdown: list[str] = [
        "# Qualitative Answer Evaluation",
        "",
        f"Dataset: `{review_set.dataset_id}`",
        "",
        f"Dataset version: `{review_set.dataset_version}`",
        "",
        (
            "Answer baseline generated: "
            f"`{review_set.answer_baseline_generated_at.isoformat()}`"
        ),
        "",
        f"Generation model: `{review_set.generation_model}`",
        "",
        f"Reviewed: `{review_set.reviewed_at.isoformat()}`",
        "",
        "## Summary",
        "",
        f"- Answerable cases reviewed: **{summary.total_reviews}**",
        f"- Strict passes: **{summary.passed_reviews}**",
        f"- Strict failures: **{summary.failed_reviews}**",
        (
            "- Strict qualitative pass rate: "
            f"**{_format_percentage(summary.pass_rate)}**"
        ),
        "",
        "### Average scores",
        "",
        (
            "- Support / faithfulness: "
            f"**{summary.support_faithfulness_average:.2f} / 2**"
        ),
        (
            "- Required-point completeness: "
            f"**{summary.required_point_completeness_average:.2f} / 2**"
        ),
        (
            "- Unsupported details: "
            f"**{summary.unsupported_details_average:.2f} / 2**"
        ),
        (
            "- Focus / relevance: "
            f"**{summary.focus_relevance_average:.2f} / 2**"
        ),
        "",
        (
            "> A strict pass requires a score of 2 on all four "
            "qualitative dimensions."
        ),
        "",
        "## Case results",
        "",
    ]

    for review in review_set.reviews:
        markdown.extend(
            [
                (
                    f"### {review.case_id} — "
                    f"{'PASS' if review.passed else 'FAIL'}"
                ),
                "",
                (
                    "- Support / faithfulness: "
                    f"**{review.support_faithfulness_score} / 2**"
                ),
                (
                    "- Required-point completeness: "
                    f"**{review.required_point_completeness_score} / 2**"
                ),
                (
                    "- Unsupported details: "
                    f"**{review.unsupported_details_score} / 2**"
                ),
                (
                    "- Focus / relevance: "
                    f"**{review.focus_relevance_score} / 2**"
                ),
                "",
            ]
        )

        if review.notes:
            markdown.extend(
                [
                    f"**Notes:** {review.notes}",
                    "",
                ]
            )

        markdown.extend(
            [
                "---",
                "",
            ]
        )

    OUTPUT_PATH.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print(
        "PASS: Qualitative answer evaluation written to "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()