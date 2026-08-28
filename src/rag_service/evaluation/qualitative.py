"""Models for human qualitative answer evaluation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QualitativeAnswerReview(BaseModel):
    """Human qualitative scores for one generated answer."""

    model_config = ConfigDict(extra="forbid")

    case_id: str

    support_faithfulness_score: int = Field(
        ge=0,
        le=2,
    )
    required_point_completeness_score: int = Field(
        ge=0,
        le=2,
    )
    unsupported_details_score: int = Field(
        ge=0,
        le=2,
    )
    focus_relevance_score: int = Field(
        ge=0,
        le=2,
    )

    notes: str | None = None

    @property
    def passed(self) -> bool:
        """Return whether the answer passed all qualitative checks."""

        return all(
            score == 2
            for score in (
                self.support_faithfulness_score,
                self.required_point_completeness_score,
                self.unsupported_details_score,
                self.focus_relevance_score,
            )
        )


class QualitativeAnswerReviewSet(BaseModel):
    """Human reviews for one answer-evaluation run."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    dataset_version: str
    answer_baseline_generated_at: datetime
    generation_model: str
    reviewed_at: datetime
    reviews: list[QualitativeAnswerReview]

    @model_validator(mode="after")
    def validate_unique_case_ids(self) -> Self:
        case_ids = [
            review.case_id
            for review in self.reviews
        ]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError(
                "Qualitative review case IDs must be unique."
            )

        return self

def load_qualitative_answer_review(
    path: str | Path,
) -> QualitativeAnswerReviewSet:
    """Load and validate a qualitative answer review from JSON."""

    review_path = Path(path)

    return QualitativeAnswerReviewSet.model_validate_json(
        review_path.read_text(encoding="utf-8")
    )


def validate_review_against_answer_baseline(
    review_set: QualitativeAnswerReviewSet,
    baseline_path: str | Path,
) -> None:
    """Validate that human reviews match the answer baseline they review."""

    baseline = json.loads(
        Path(baseline_path).read_text(encoding="utf-8")
    )

    _validate_baseline_identity(
        review_set,
        baseline,
    )

    expected_case_ids = {
        case["case_id"]
        for case in baseline["cases"]
        if case["expected_answer"][
            "expected_sufficient_evidence"
        ]
    }

    reviewed_case_ids = {
        review.case_id
        for review in review_set.reviews
    }

    missing_case_ids = expected_case_ids - reviewed_case_ids
    unexpected_case_ids = reviewed_case_ids - expected_case_ids

    if missing_case_ids or unexpected_case_ids:
        problems: list[str] = []

        if missing_case_ids:
            problems.append(
                "missing reviews for: "
                + ", ".join(sorted(missing_case_ids))
            )

        if unexpected_case_ids:
            problems.append(
                "unexpected reviews for: "
                + ", ".join(sorted(unexpected_case_ids))
            )

        raise ValueError(
            "Qualitative reviews do not match answerable "
            "baseline cases: "
            + "; ".join(problems)
        )


def _validate_baseline_identity(
    review_set: QualitativeAnswerReviewSet,
    baseline: dict[str, Any],
) -> None:
    """Validate that review metadata identifies the same baseline run."""

    if review_set.dataset_id != baseline["dataset_id"]:
        raise ValueError(
            "Qualitative review dataset ID does not match "
            "the answer baseline."
        )

    if review_set.dataset_version != baseline["dataset_version"]:
        raise ValueError(
            "Qualitative review dataset version does not match "
            "the answer baseline."
        )

    baseline_generated_at = datetime.fromisoformat(
        baseline["generated_at"]
    )

    if (
        review_set.answer_baseline_generated_at
        != baseline_generated_at
    ):
        raise ValueError(
            "Qualitative review does not match the answer "
            "baseline generation time."
        )

    if review_set.generation_model != baseline["generation_model"]:
        raise ValueError(
            "Qualitative review generation model does not match "
            "the answer baseline."
        )

class QualitativeAnswerSummary(BaseModel):
    """Summary metrics for human qualitative answer reviews."""

    model_config = ConfigDict(extra="forbid")

    total_reviews: int
    passed_reviews: int
    failed_reviews: int
    pass_rate: float

    support_faithfulness_average: float
    required_point_completeness_average: float
    unsupported_details_average: float
    focus_relevance_average: float


def summarize_qualitative_reviews(
    review_set: QualitativeAnswerReviewSet,
) -> QualitativeAnswerSummary:
    """Calculate summary metrics for qualitative reviews."""

    reviews = review_set.reviews

    if not reviews:
        raise ValueError(
            "Cannot summarize an empty qualitative review set."
        )

    passed_reviews = sum(
        review.passed
        for review in reviews
    )

    total_reviews = len(reviews)

    return QualitativeAnswerSummary(
        total_reviews=total_reviews,
        passed_reviews=passed_reviews,
        failed_reviews=total_reviews - passed_reviews,
        pass_rate=passed_reviews / total_reviews,
        support_faithfulness_average=(
            sum(
                review.support_faithfulness_score
                for review in reviews
            )
            / total_reviews
        ),
        required_point_completeness_average=(
            sum(
                review.required_point_completeness_score
                for review in reviews
            )
            / total_reviews
        ),
        unsupported_details_average=(
            sum(
                review.unsupported_details_score
                for review in reviews
            )
            / total_reviews
        ),
        focus_relevance_average=(
            sum(
                review.focus_relevance_score
                for review in reviews
            )
            / total_reviews
        ),
    )