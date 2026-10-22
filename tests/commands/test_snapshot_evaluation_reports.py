"""Check that published snapshots preserve matching saved runs."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rag_service.commands.snapshot_evaluation_reports import create_snapshot


class SnapshotTests(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dataset_path = self.root / "baseline.json"
        self.source = self.root / "saved"
        self.source.mkdir()
        self.output = self.root / "reports"
        source = {
            "document_id": "doc-1",
            "title": "Metadata",
            "heading_path": [],
            "chunk_id": None,
            "role": "primary",
        }
        answer = {"expected_sufficient_evidence": True, "required_points": ["Tags"]}
        self.dataset = {
            "dataset_id": "doc-landscape-baseline",
            "version": "1.7",
            "cases": [
                {
                    "id": "case-1",
                    "category": "exact_answer",
                    "query": "Why tags?",
                    "retrieval": {"relevant_sources": [source]},
                    "answer": answer,
                }
            ],
        }
        self.dataset_path.write_text(json.dumps(self.dataset))
        base = {
            "dataset_id": "doc-landscape-baseline",
            "dataset_version": "1.7",
            "generated_at": "2026-10-18T10:00:00+00:00",
            "collection": "rag_chunks",
            "embedding_model": "embedding-model",
        }
        case = {
            "case_id": "case-1",
            "category": "exact_answer",
            "query": "Why tags?",
            "passed": True,
        }
        self.retrieval = dict(
            base, cases=[dict(case, expected_empty=False, expected_sources=[source])]
        )
        self.answer = dict(
            base,
            generation_model="answer-model",
            cases=[dict(case, expected_answer=answer)],
        )
        self.review = {
            "dataset_id": base["dataset_id"],
            "dataset_version": "1.7",
            "answer_baseline_generated_at": "2026-10-18T10:00:00Z",
            "generation_model": "answer-model",
            "reviewed_at": "2026-10-18T11:00:00Z",
            "reviews": [
                {
                    "case_id": "case-1",
                    "support_faithfulness_score": 2,
                    "required_point_completeness_score": 2,
                    "unsupported_details_score": 2,
                    "focus_relevance_score": 2,
                }
            ],
        }
        self.write_json("retrieval_baseline", self.retrieval)
        self.write_json("answer_baseline", self.answer)
        markdown = (
            "Generated: 2026-10-18T10:00:00Z\n"
            "Dataset: `doc-landscape-baseline`\nDataset version: `1.7`\n"
            "Collection: `rag_chunks`\nEmbedding model: `embedding-model`\n"
        )
        (self.source / "retrieval_baseline.md").write_text(
            markdown + "### case-1 — PASS\n"
        )
        (self.source / "answer_baseline.md").write_text(
            markdown + "Generation model: `answer-model`\n### case-1 — PASS\n"
        )
        self.write_json("answer_qualitative_review", self.review)
        (self.source / "answer_qualitative_review.md").write_text(
            "Dataset: `doc-landscape-baseline`\nDataset version: `1.7`\n"
            "Answer baseline generated: `2026-10-18T10:00:00+00:00`\n"
            "Generation model: `answer-model`\nReviewed: `2026-10-18T11:00:00+00:00`\n"
            "### case-1 — PASS\n"
        )

    def write_json(self, stem: str, report: dict) -> None:
        (self.source / f"{stem}.json").write_text(json.dumps(report))

    def snapshot(self, *, review: bool = False, name: str | None = None) -> Path:
        return create_snapshot(
            dataset_path=self.dataset_path,
            source_dir=self.source,
            output_dir=self.output,
            include_review=review,
            name=name,
        )

    def test_preserves_bytes_and_checksums(self) -> None:
        target = self.snapshot()
        self.assertRegex(target.name, r"^doc-landscape-v1\.7-\d{4}-\d{2}-\d{2}$")
        manifest = json.loads((target / "manifest.json").read_text())
        self.assertEqual(len(manifest["files"]), 5)
        for item in manifest["files"]:
            original = (
                self.dataset_path
                if item["name"] == "baseline.json"
                else self.source / item["name"]
            ).read_bytes()
            self.assertEqual((target / item["name"]).read_bytes(), original)
            self.assertEqual(item["sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(item["size_bytes"], len(original))
        self.assertIsNone(manifest["reviewed_at"])
        self.assertFalse((target / "answer_qualitative_review.json").exists())

    def test_matching_review_accepts_equivalent_timestamp_formats(self) -> None:
        target = self.snapshot(review=True)
        manifest = json.loads((target / "manifest.json").read_text())
        self.assertEqual(len(manifest["files"]), 7)
        self.assertEqual(
            (target / "answer_qualitative_review.json").read_bytes(),
            (self.source / "answer_qualitative_review.json").read_bytes(),
        )

    def test_rejects_different_dataset_version(self) -> None:
        self.answer["dataset_version"] = "1.5"
        self.write_json("answer_baseline", self.answer)
        with self.assertRaisesRegex(ValueError, "dataset ID or version"):
            self.snapshot()
        self.assertFalse(self.output.exists())

    def test_rejects_changed_expectations_even_if_version_matches(self) -> None:
        self.retrieval["cases"][0]["expected_sources"] = []
        self.write_json("retrieval_baseline", self.retrieval)
        with self.assertRaisesRegex(ValueError, "expectations differ"):
            self.snapshot()

    def test_rejects_missing_and_duplicate_cases(self) -> None:
        original = self.answer["cases"][:]
        for cases in ([], original + original):
            with self.subTest(cases=cases):
                self.answer["cases"] = cases
                self.write_json("answer_baseline", self.answer)
                with self.assertRaisesRegex(ValueError, "case IDs differ"):
                    self.snapshot()

    def test_rejects_stale_markdown(self) -> None:
        path = self.source / "answer_baseline.md"
        path.write_text(path.read_text().replace("T10:00:00Z", "T09:00:00Z"))
        with self.assertRaisesRegex(ValueError, "Generated differs"):
            self.snapshot()

    def test_rejects_inconsistent_markdown_case_results(self) -> None:
        path = self.source / "retrieval_baseline.md"
        path.write_text(path.read_text().replace("PASS", "FAIL"))
        with self.assertRaisesRegex(ValueError, "case results differ"):
            self.snapshot()

    def test_rejects_stale_review_and_cleans_staging(self) -> None:
        self.review["answer_baseline_generated_at"] = "2026-10-17T10:00:00Z"
        self.write_json("answer_qualitative_review", self.review)
        path = self.source / "answer_qualitative_review.md"
        path.write_text(path.read_text().replace("18T10", "17T10"))
        with self.assertRaisesRegex(ValueError, "generation time"):
            self.snapshot(review=True)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_rejects_incomplete_review_coverage(self) -> None:
        self.review["reviews"] = []
        self.write_json("answer_qualitative_review", self.review)
        path = self.source / "answer_qualitative_review.md"
        path.write_text(path.read_text().replace("### case-1 — PASS\n", ""))
        with self.assertRaisesRegex(ValueError, "missing reviews"):
            self.snapshot(review=True)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_never_overwrites_an_existing_snapshot(self) -> None:
        target = self.snapshot(name="saved-run")
        before = {p.name: p.read_bytes() for p in target.iterdir()}
        with self.assertRaises(FileExistsError):
            self.snapshot(name="saved-run")
        self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})
        (self.output / "empty-folder").mkdir()
        with self.assertRaises(FileExistsError):
            self.snapshot(name="empty-folder")

    def test_requires_complete_report_pairs(self) -> None:
        (self.source / "answer_baseline.md").unlink()
        with self.assertRaises(FileNotFoundError):
            self.snapshot()
        self.assertFalse(self.output.exists())

    def test_rejects_path_traversal(self) -> None:
        with self.assertRaisesRegex(ValueError, "Snapshot name"):
            self.snapshot(name="../outside")

    def test_cli_creates_snapshot_without_provider_configuration(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "rag_service.commands.snapshot_evaluation_reports",
                "--dataset",
                str(self.dataset_path),
                "--source-dir",
                str(self.source),
                "--output-dir",
                str(self.output),
                "--name",
                "cli-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.output / "cli-run" / "manifest.json").is_file())
