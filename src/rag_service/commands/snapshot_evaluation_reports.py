"""Preserve saved evaluation reports and their dataset in a new snapshot folder."""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from rag_service.evaluation.models import EvaluationDataset
from rag_service.evaluation.qualitative import (
    QualitativeAnswerReviewSet,
    validate_review_against_answer_baseline,
)


def _timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        raise ValueError("Report timestamps must include a timezone.")
    return timestamp


def _check_markdown(
    contents: bytes,
    *,
    name: str,
    metadata: dict[str, str | datetime],
    cases: list[tuple[str, bool]],
) -> None:
    text = contents.decode("utf-8")
    for label, expected in metadata.items():
        values = re.findall(rf"^{re.escape(label)}: (.+)$", text, re.MULTILINE)
        if len(values) != 1:
            raise ValueError(f"{name}: missing or duplicate {label!r} header.")
        actual = values[0].strip().strip("`")
        matches = (
            _timestamp(actual) == expected
            if isinstance(expected, datetime)
            else actual == expected
        )
        if not matches:
            raise ValueError(f"{name}: {label} differs from the JSON report.")

    headings = re.findall(r"^### (\S+) — (PASS|FAIL)$", text, re.MULTILINE)
    expected_headings = [
        (case_id, "PASS" if passed else "FAIL") for case_id, passed in cases
    ]
    if headings != expected_headings:
        raise ValueError(f"{name}: case results differ from the JSON report.")


def _check_report(
    report: dict[str, Any],
    dataset: EvaluationDataset,
    *,
    kind: str,
) -> None:
    if (report["dataset_id"], report["dataset_version"]) != (
        dataset.dataset_id,
        dataset.version,
    ):
        raise ValueError(f"{kind}: dataset ID or version differs from the dataset.")
    _timestamp(report["generated_at"])
    cases = report["cases"]
    by_id = {case["case_id"]: case for case in cases}
    if len(by_id) != len(cases) or set(by_id) != {case.id for case in dataset.cases}:
        raise ValueError(f"{kind}: case IDs differ from the dataset.")
    for case in dataset.cases:
        saved = by_id[case.id]
        if saved["query"] != case.query or saved["category"] != case.category:
            raise ValueError(f"{kind}: query or category differs for {case.id}.")
        if not isinstance(saved["passed"], bool):
            raise ValueError(f"{kind}: invalid pass/fail value for {case.id}.")
        if kind == "retrieval":
            matches = saved["expected_empty"] == case.retrieval.expect_empty and saved[
                "expected_sources"
            ] == [source.model_dump() for source in case.retrieval.relevant_sources]
        else:
            matches = (
                case.answer is not None
                and saved["expected_answer"] == case.answer.model_dump()
            )
        if not matches:
            raise ValueError(f"{kind}: saved expectations differ for {case.id}.")


def create_snapshot(
    *,
    dataset_path: Path,
    source_dir: Path,
    output_dir: Path,
    name: str | None = None,
    include_review: bool = False,
) -> Path:
    """Copy validated saved artifacts without changing their original bytes."""
    dataset_bytes = dataset_path.read_bytes()
    dataset = EvaluationDataset.model_validate_json(dataset_bytes)
    if not dataset.cases:
        raise ValueError("Cannot snapshot reports for an empty dataset.")
    assembled = datetime.now(UTC)
    prefix = dataset.dataset_id.removesuffix("-baseline")
    snapshot_id = name or f"{prefix}-v{dataset.version}-{assembled.date()}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", snapshot_id):
        raise ValueError("Snapshot name must use letters, numbers, dots, '_' or '-'.")
    destination = output_dir / snapshot_id
    if destination.exists():
        raise FileExistsError(
            f"Snapshot already exists: {destination}. Use --name for another set."
        )

    files = {"baseline.json": dataset_bytes}
    reports: dict[str, dict[str, Any]] = {}
    for kind in ("retrieval", "answer"):
        stem = f"{kind}_baseline"
        for extension in ("json", "md"):
            filename = f"{stem}.{extension}"
            files[filename] = (source_dir / filename).read_bytes()
        report = json.loads(files[f"{stem}.json"])
        _check_report(report, dataset, kind=kind)
        metadata: dict[str, str | datetime] = {
            "Generated": _timestamp(report["generated_at"]),
            "Dataset": dataset.dataset_id,
            "Dataset version": dataset.version,
            "Collection": report["collection"],
            "Embedding model": report["embedding_model"],
        }
        if kind == "answer":
            metadata["Generation model"] = report["generation_model"]
        _check_markdown(
            files[f"{stem}.md"],
            name=f"{stem}.md",
            metadata=metadata,
            cases=[(case["case_id"], case["passed"]) for case in report["cases"]],
        )
        reports[kind] = report

    review = None
    if include_review:
        for extension in ("json", "md"):
            filename = f"answer_qualitative_review.{extension}"
            files[filename] = (source_dir / filename).read_bytes()
        review = QualitativeAnswerReviewSet.model_validate_json(
            files["answer_qualitative_review.json"]
        )
        _check_markdown(
            files["answer_qualitative_review.md"],
            name="answer_qualitative_review.md",
            metadata={
                "Dataset": review.dataset_id,
                "Dataset version": review.dataset_version,
                "Answer baseline generated": review.answer_baseline_generated_at,
                "Generation model": review.generation_model,
                "Reviewed": review.reviewed_at,
            },
            cases=[(item.case_id, item.passed) for item in review.reviews],
        )

    manifest = {
        "snapshot_id": snapshot_id,
        "assembled_on": assembled.date().isoformat(),
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.version,
        "retrieval_generated_at": reports["retrieval"]["generated_at"],
        "answer_generated_at": reports["answer"]["generated_at"],
        "reviewed_at": review.reviewed_at.isoformat() if review else None,
        "answer_baseline_generated_at": (
            review.answer_baseline_generated_at.isoformat() if review else None
        ),
        "implementation_commit": None,
        "historical_corpus_snapshot": None,
        "files": [
            {
                "name": filename,
                "size_bytes": len(contents),
                "sha256": hashlib.sha256(contents).hexdigest(),
            }
            for filename, contents in sorted(files.items())
        ],
    }
    readme = (
        f"# Evaluation snapshot: {snapshot_id}\n\n"
        f"Dataset: `{dataset.dataset_id}`, version `{dataset.version}`.\n\n"
        "| Artifact | Recorded time |\n| --- | --- |\n"
        f"| Retrieval baseline | {reports['retrieval']['generated_at']} |\n"
        f"| Answer baseline | {reports['answer']['generated_at']} |\n"
        + (f"| Human review | {review.reviewed_at.isoformat()} |\n" if review else "")
        + "\nRead the Markdown reports for results and the JSON files for exact "
        "values. `baseline.json` preserves the dataset used for this set.\n\n"
        + (
            "The human review was validated against the saved answer report.\n\n"
            if review
            else "Human review is not included in this set.\n\n"
        )
        + "`manifest.json` records run dates and file checksums. The implementation "
        "commit and full historical corpus/index are not captured. Report fields "
        "do not preserve every setting or dataset input; matching metadata and "
        "saved expectations alone cannot establish an identical environment.\n\n"
        "Keep published files unchanged. Save later runs in a new folder.\n"
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".evaluation-snapshot-", dir=output_dir) as temp:
        staging = Path(temp) / "snapshot"
        staging.mkdir()
        for filename, contents in files.items():
            (staging / filename).write_bytes(contents)
        if review:
            validate_review_against_answer_baseline(
                review, staging / "answer_baseline.json"
            )
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (staging / "README.md").write_text(readme, encoding="utf-8")
        # Reserve the destination exclusively so even an empty folder is preserved.
        destination.mkdir()
        try:
            staging.replace(destination)
        except OSError:
            destination.rmdir()
            raise
    return destination


def main() -> None:
    """Package existing reports; no live evaluation or provider calls are made."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=Path("evaluation/datasets/baseline.json")
    )
    parser.add_argument(
        "--source-dir", type=Path, default=Path("data/evaluation/latest")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/reports"))
    parser.add_argument("--name", help="Override the version-and-UTC-date folder name.")
    parser.add_argument(
        "--include-review",
        action="store_true",
        help="Include and validate human review.",
    )
    args = parser.parse_args()
    try:
        destination = create_snapshot(
            dataset_path=args.dataset,
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            name=args.name,
            include_review=args.include_review,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print(f"Saved evaluation snapshot: {destination}")


if __name__ == "__main__":
    main()
