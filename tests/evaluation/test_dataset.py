from pathlib import Path

import pytest
from pydantic import ValidationError

from rag_service.evaluation.dataset import load_evaluation_dataset


def test_load_evaluation_dataset(tmp_path: Path) -> None:
    dataset_path = tmp_path / "baseline.json"

    dataset_path.write_text(
        """
        {
          "dataset_id": "baseline",
          "version": "1.0",
          "description": "Baseline evaluation dataset.",
          "cases": [
            {
              "id": "metadata-001",
              "category": "exact_answer",
              "query": "How does metadata improve retrieval?",
              "filters": {
                "source": "wordpress"
              },
              "retrieval": {
                "relevant_sources": [
                  {
                    "chunk_id": "chunk-1",
                    "document_id": "document-1",
                    "title": "Metadata Strategy",
                    "heading_path": [
                      "Metadata filtering"
                    ]
                  }
                ],
                "expect_empty": false
              },
              "answer": null
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    dataset = load_evaluation_dataset(dataset_path)

    assert dataset.dataset_id == "baseline"
    assert dataset.version == "1.0"
    assert len(dataset.cases) == 1
    assert dataset.cases[0].id == "metadata-001"


def test_load_evaluation_dataset_validates_contents(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "invalid.json"

    dataset_path.write_text(
        """
        {
          "dataset_id": "baseline",
          "version": "1.0",
          "cases": [
            {
              "id": "bad-case",
              "category": "exact_answer",
              "query": "Test query",
              "retrieval": {
                "relevant_sources": [],
                "expect_empty": false
              }
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
        match="must define at least one relevant source",
    ):
        load_evaluation_dataset(dataset_path)


def test_load_evaluation_dataset_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "invalid.json"

    dataset_path.write_text(
        "{not valid json}",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_evaluation_dataset(dataset_path)


def test_load_evaluation_dataset_raises_for_missing_file(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_evaluation_dataset(dataset_path)

def test_repository_baseline_dataset_is_valid() -> None:
    dataset = load_evaluation_dataset(
        "evaluation/datasets/baseline.json"
    )

    assert dataset.dataset_id == "doc-landscape-baseline"
    assert dataset.version == "1.5"
    assert len(dataset.cases) == 22