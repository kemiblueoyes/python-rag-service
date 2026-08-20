from pathlib import Path

from rag_service.evaluation.models import EvaluationDataset


def load_evaluation_dataset(
    path: str | Path,
) -> EvaluationDataset:
    """Load and validate an evaluation dataset from JSON."""

    dataset_path = Path(path)

    return EvaluationDataset.model_validate_json(
        dataset_path.read_text(encoding="utf-8")
    )