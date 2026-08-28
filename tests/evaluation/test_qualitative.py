import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from rag_service.evaluation.qualitative import (
    QualitativeAnswerReview,
    QualitativeAnswerReviewSet,
    load_qualitative_answer_review,
    validate_review_against_answer_baseline,
)


def test_qualitative_review_passes_when_all_scores_are_two() -> None:
    review = QualitativeAnswerReview(
        case_id="case-001",
        support_faithfulness_score=2,
        required_point_completeness_score=2,
        unsupported_details_score=2,
        focus_relevance_score=2,
    )

    assert review.passed is True


def test_qualitative_review_fails_when_any_score_is_below_two() -> None:
    review = QualitativeAnswerReview(
        case_id="case-001",
        support_faithfulness_score=2,
        required_point_completeness_score=2,
        unsupported_details_score=2,
        focus_relevance_score=1,
    )

    assert review.passed is False


@pytest.mark.parametrize(
    "field_name",
    [
        "support_faithfulness_score",
        "required_point_completeness_score",
        "unsupported_details_score",
        "focus_relevance_score",
    ],
)
def test_qualitative_review_rejects_scores_above_two(
    field_name: str,
) -> None:
    values = {
        "case_id": "case-001",
        "support_faithfulness_score": 2,
        "required_point_completeness_score": 2,
        "unsupported_details_score": 2,
        "focus_relevance_score": 2,
    }
    values[field_name] = 3

    with pytest.raises(ValidationError):
        QualitativeAnswerReview(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "support_faithfulness_score",
        "required_point_completeness_score",
        "unsupported_details_score",
        "focus_relevance_score",
    ],
)
def test_qualitative_review_rejects_scores_below_zero(
    field_name: str,
) -> None:
    values = {
        "case_id": "case-001",
        "support_faithfulness_score": 2,
        "required_point_completeness_score": 2,
        "unsupported_details_score": 2,
        "focus_relevance_score": 2,
    }
    values[field_name] = -1

    with pytest.raises(ValidationError):
        QualitativeAnswerReview(**values)


def test_qualitative_review_set_accepts_unique_case_ids() -> None:
    review_set = QualitativeAnswerReviewSet(
        dataset_id="doc-landscape-baseline",
        dataset_version="1.5",
        answer_baseline_generated_at=datetime(
            2026,
            8,
            28,
            1,
            47,
            tzinfo=UTC,
        ),
        generation_model="gpt-5.6-terra",
        reviewed_at=datetime(
            2026,
            8,
            28,
            2,
            0,
            tzinfo=UTC,
        ),
        reviews=[
            QualitativeAnswerReview(
                case_id="case-001",
                support_faithfulness_score=2,
                required_point_completeness_score=2,
                unsupported_details_score=2,
                focus_relevance_score=2,
            ),
            QualitativeAnswerReview(
                case_id="case-002",
                support_faithfulness_score=2,
                required_point_completeness_score=2,
                unsupported_details_score=2,
                focus_relevance_score=1,
            ),
        ],
    )

    assert len(review_set.reviews) == 2


def test_qualitative_review_set_rejects_duplicate_case_ids() -> None:
    duplicate_review = QualitativeAnswerReview(
        case_id="case-001",
        support_faithfulness_score=2,
        required_point_completeness_score=2,
        unsupported_details_score=2,
        focus_relevance_score=2,
    )

    with pytest.raises(
        ValidationError,
        match="Qualitative review case IDs must be unique",
    ):
        QualitativeAnswerReviewSet(
            dataset_id="doc-landscape-baseline",
            dataset_version="1.5",
            answer_baseline_generated_at=datetime(
                2026,
                8,
                28,
                1,
                47,
                tzinfo=UTC,
            ),
            generation_model="gpt-5.6-terra",
            reviewed_at=datetime(
                2026,
                8,
                28,
                2,
                0,
                tzinfo=UTC,
            ),
            reviews=[
                duplicate_review,
                duplicate_review,
            ],
        )

def _write_answer_baseline(
    path: Path,
    *,
    dataset_id: str = "doc-landscape-baseline",
    dataset_version: str = "1.4",
    generated_at: str = "2026-08-28T01:47:37.065056+00:00",
    generation_model: str = "gpt-5.6-terra",
) -> None:
    path.write_text(
        json.dumps(
            {
                "dataset_id": dataset_id,
                "dataset_version": dataset_version,
                "generated_at": generated_at,
                "generation_model": generation_model,
                "cases": [
                    {
                        "case_id": "case-001",
                        "expected_answer": {
                            "expected_sufficient_evidence": True,
                        },
                    },
                    {
                        "case_id": "case-002",
                        "expected_answer": {
                            "expected_sufficient_evidence": True,
                        },
                    },
                    {
                        "case_id": "case-empty",
                        "expected_answer": {
                            "expected_sufficient_evidence": False,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _make_review_set() -> QualitativeAnswerReviewSet:
    return QualitativeAnswerReviewSet(
        dataset_id="doc-landscape-baseline",
        dataset_version="1.4",
        answer_baseline_generated_at=datetime.fromisoformat(
            "2026-08-28T01:47:37.065056+00:00"
        ),
        generation_model="gpt-5.6-terra",
        reviewed_at=datetime(
            2026,
            8,
            28,
            2,
            0,
            tzinfo=UTC,
        ),
        reviews=[
            QualitativeAnswerReview(
                case_id="case-001",
                support_faithfulness_score=2,
                required_point_completeness_score=2,
                unsupported_details_score=2,
                focus_relevance_score=2,
            ),
            QualitativeAnswerReview(
                case_id="case-002",
                support_faithfulness_score=2,
                required_point_completeness_score=2,
                unsupported_details_score=2,
                focus_relevance_score=2,
            ),
        ],
    )


def test_load_qualitative_answer_review(
    tmp_path: Path,
) -> None:
    path = tmp_path / "review.json"

    review_set = _make_review_set()

    path.write_text(
        review_set.model_dump_json(),
        encoding="utf-8",
    )

    loaded = load_qualitative_answer_review(path)

    assert loaded == review_set


def test_validate_review_against_answer_baseline_passes(
    tmp_path: Path,
) -> None:
    baseline_path = tmp_path / "answer_baseline.json"
    _write_answer_baseline(baseline_path)

    validate_review_against_answer_baseline(
        _make_review_set(),
        baseline_path,
    )


def test_validate_review_rejects_missing_answerable_case(
    tmp_path: Path,
) -> None:
    baseline_path = tmp_path / "answer_baseline.json"
    _write_answer_baseline(baseline_path)

    review_set = _make_review_set()
    review_set.reviews.pop()

    with pytest.raises(
        ValueError,
        match="missing reviews for: case-002",
    ):
        validate_review_against_answer_baseline(
            review_set,
            baseline_path,
        )


def test_validate_review_rejects_unexpected_case(
    tmp_path: Path,
) -> None:
    baseline_path = tmp_path / "answer_baseline.json"
    _write_answer_baseline(baseline_path)

    review_set = _make_review_set()
    review_set.reviews.append(
        QualitativeAnswerReview(
            case_id="case-empty",
            support_faithfulness_score=2,
            required_point_completeness_score=2,
            unsupported_details_score=2,
            focus_relevance_score=2,
        )
    )

    with pytest.raises(
        ValueError,
        match="unexpected reviews for: case-empty",
    ):
        validate_review_against_answer_baseline(
            review_set,
            baseline_path,
        )


def test_validate_review_rejects_dataset_version_mismatch(
    tmp_path: Path,
) -> None:
    baseline_path = tmp_path / "answer_baseline.json"
    _write_answer_baseline(
        baseline_path,
        dataset_version="1.5",
    )

    with pytest.raises(
        ValueError,
        match="dataset version does not match",
    ):
        validate_review_against_answer_baseline(
            _make_review_set(),
            baseline_path,
        )


def test_validate_review_rejects_generation_time_mismatch(
    tmp_path: Path,
) -> None:
    baseline_path = tmp_path / "answer_baseline.json"
    _write_answer_baseline(
        baseline_path,
        generated_at="2026-08-28T03:00:00+00:00",
    )

    with pytest.raises(
        ValueError,
        match="generation time",
    ):
        validate_review_against_answer_baseline(
            _make_review_set(),
            baseline_path,
        )


def test_validate_review_rejects_generation_model_mismatch(
    tmp_path: Path,
) -> None:
    baseline_path = tmp_path / "answer_baseline.json"
    _write_answer_baseline(
        baseline_path,
        generation_model="different-model",
    )

    with pytest.raises(
        ValueError,
        match="generation model does not match",
    ):
        validate_review_against_answer_baseline(
            _make_review_set(),
            baseline_path,
        )

