import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from rag_service.commands import evaluate_retrieval as evaluator
from rag_service.commands.index_wordpress import WordPressIndexResult
from rag_service.config import settings
from rag_service.indexing.change_detection import DocumentChanges
from rag_service.indexing.vector_index import VectorIndexStats
from rag_service.operations import adapters
from rag_service.operations.app import create_app
from tests.operations.test_runner import completed, submit


@pytest.fixture
def evaluation_setup(tmp_path, monkeypatch):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps(
            {
                "dataset_id": "test-baseline",
                "version": "1",
                "cases": [
                    {
                        "id": "missing-primary",
                        "category": "exact_answer",
                        "query": "Question",
                        "retrieval": {
                            "relevant_sources": [{"document_id": "doc", "title": "Doc"}]
                        },
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(evaluator, "DATASET_PATH", dataset)
    monkeypatch.setattr(adapters, "RUNS_DIRECTORY", tmp_path / "runs")
    monkeypatch.setattr(settings, "voyage_api_key", "SECRET")
    monkeypatch.setattr(settings, "qdrant_url", "http://localhost:6333")
    services = []

    def factory(_settings):
        service = MagicMock()
        service.retrieve.return_value = []
        services.append(service)
        return service

    monkeypatch.setattr(evaluator, "create_retrieval_service", factory)
    return dataset, services


def test_evaluation_fresh_services_reports_and_failed_cases(evaluation_setup, tmp_path):
    _, services = evaluation_setup
    first = adapters.evaluate("first")
    second = adapters.evaluate("second")
    assert first["failed_case_ids"] == ["missing-primary"]
    assert first["summary"]["overall_success_rate"] == 0
    assert first["report_paths"] != second["report_paths"]
    assert len(services) == 2
    for service in services:
        service.close.assert_called_once_with()
    for report in (first, second):
        assert report["dataset_id"] == "test-baseline"
        assert report["dataset_version"] == "1"
        assert "SECRET" not in json.dumps(report)
        for path in report["report_paths"].values():
            assert Path(path).is_file()


def test_failed_cases_are_successful_execution(evaluation_setup, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "operations_api_key", SecretStr("operations-test"))
    with TestClient(
        create_app(
            tmp_path / "jobs.db",
            {
                "evaluate_retrieval": adapters.evaluate,
            },
        )
    ) as client:
        result = completed(client, submit(client, "evaluate_retrieval").json())
        assert result["status"] == "succeeded"
        assert result["result"]["failed_case_ids"] == ["missing-primary"]


def test_failed_evaluation_never_returns_stale_report(
    evaluation_setup, tmp_path, monkeypatch
):
    adapters.evaluate("previous")
    broken = MagicMock()
    broken.retrieve.side_effect = RuntimeError("SECRET")
    monkeypatch.setattr(evaluator, "create_retrieval_service", lambda _: broken)
    monkeypatch.setattr(settings, "operations_api_key", SecretStr("operations-test"))
    with TestClient(
        create_app(
            tmp_path / "jobs.db",
            {
                "evaluate_retrieval": adapters.evaluate,
            },
        )
    ) as client:
        result = completed(client, submit(client, "evaluate_retrieval").json())
        assert result["status"] == "failed"
        assert result["result"] is None
        assert not (tmp_path / "runs" / result["job_id"]).exists()
    broken.close.assert_called_once_with()
    assert (tmp_path / "runs/previous/retrieval_baseline.json").exists()


def test_report_write_failure_closes_service(evaluation_setup, tmp_path):
    dataset, services = evaluation_setup
    blocker = tmp_path / "not-directory"
    blocker.write_text("blocking file")
    with pytest.raises(OSError):
        evaluator.run(dataset, tmp_path / "report.json", blocker / "report.md")
    services[0].close.assert_called_once_with()


def test_cli_preserves_message_and_default_paths(evaluation_setup, monkeypatch, capsys):
    run = MagicMock()
    monkeypatch.setattr(evaluator, "run", run)
    evaluator.main()
    run.assert_called_once_with(
        evaluator.DATASET_PATH,
        Path("data/evaluation/latest/retrieval_baseline.json"),
        Path("data/evaluation/latest/retrieval_baseline.md"),
    )
    assert capsys.readouterr().out == (
        "PASS: Retrieval evaluation written to "
        "data/evaluation/latest/retrieval_baseline.json and "
        "data/evaluation/latest/retrieval_baseline.md\n"
    )


def test_index_incremental_counts_and_cleanup(monkeypatch):
    embedding, vector = MagicMock(), MagicMock()
    monkeypatch.setattr(adapters, "create_embedding_provider", lambda _: embedding)
    monkeypatch.setattr(adapters, "create_vector_store", lambda _: vector)
    run = MagicMock(
        return_value=WordPressIndexResult(
            changes=DocumentChanges(
                new=[object()], updated=[], unchanged=[], removed=[]
            ),
            vector_index=VectorIndexStats(
                documents_indexed=1, chunks_indexed=4, documents_deleted=1
            ),
        )
    )
    monkeypatch.setattr(adapters.index_wordpress, "run", run)
    result = adapters.index("job")
    assert result["new"] == 1
    assert result["changes_detected"] is True
    assert result["documents_indexed"] == 1
    assert result["chunks_indexed"] == 4
    assert result["documents_cleared"] == 1
    run.assert_called_once_with(
        adapters.DOCUMENT_PATH,
        settings.lexical_corpus_path,
        embedding_provider=embedding,
        vector_store=vector,
        embedding_batch_size=settings.embedding_batch_size,
    )
    embedding.close.assert_called_once_with()
    vector.close.assert_called_once_with()


def test_index_partial_factory_failure_closes_owned_client(monkeypatch):
    embedding = MagicMock()
    monkeypatch.setattr(adapters, "create_embedding_provider", lambda _: embedding)
    monkeypatch.setattr(
        adapters, "create_vector_store", MagicMock(side_effect=ValueError)
    )
    with pytest.raises(ValueError):
        adapters.index("job")
    embedding.close.assert_called_once_with()
