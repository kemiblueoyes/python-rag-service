import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from rag_service.config import settings
from rag_service.operations.app import create_app
from rag_service.operations.runner import Runner, RunnerUnavailable

HEADERS = {"X-API-Key": "operations-test", "Idempotency-Key": "first"}


@pytest.fixture(autouse=True)
def auth(monkeypatch):
    monkeypatch.setattr(settings, "operations_api_key", SecretStr("operations-test"))
    monkeypatch.setattr(settings, "rag_api_key", SecretStr("public-test"))


def submit(client, operation="index_wordpress", key="first"):
    return client.post(
        "/jobs",
        json={"operation": operation},
        headers={**HEADERS, "Idempotency-Key": key},
    )


def completed(client, job):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(job["status_url"], headers=HEADERS)
        assert response.status_code == 200
        if response.json()["status"] in ("succeeded", "failed"):
            return response.json()
        time.sleep(0.01)
    pytest.fail("Job did not finish")


@pytest.mark.parametrize("operation", ["index_wordpress", "evaluate_retrieval"])
def test_success_persistence_and_idempotency(tmp_path, operation):
    calls = []

    def adapter(job_id):
        calls.append(job_id)
        return {"precision": None, "failed_case_ids": ["multi-section-001"]}

    database = tmp_path / "jobs.db"
    adapters = {operation: adapter}
    with TestClient(create_app(database, adapters)) as client:
        response = submit(client, operation)
        assert response.status_code == 202
        job = completed(client, response.json())
        assert job["status"] == "succeeded"
        assert job["result"]["precision"] is None
        assert job["result"]["failed_case_ids"] == ["multi-section-001"]
        assert all(
            job[key].endswith("+00:00")
            for key in ("created_at", "started_at", "completed_at")
        )
        assert submit(client, operation).status_code == 200
    with TestClient(create_app(database, adapters)) as client:
        assert submit(client, operation).json() == job
        assert client.get("/jobs/unknown", headers=HEADERS).status_code == 404
    assert calls == [job["job_id"]]


def test_responsive_concurrent_atomic_reservation(tmp_path):
    release = threading.Event()
    started = threading.Event()
    calls = []

    def blocked(job_id):
        calls.append(job_id)
        started.set()
        assert release.wait(5)
        return {}

    adapters = {name: blocked for name in ("index_wordpress", "evaluate_retrieval")}
    with TestClient(create_app(tmp_path / "jobs.db", adapters)) as client:
        try:
            with ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(submit, client, name, name) for name in adapters]
                responses = [future.result(timeout=3) for future in futures]
            assert sorted(r.status_code for r in responses) == [202, 409]
            job = next(r.json() for r in responses if r.status_code == 202)
            assert started.wait(2)
            assert client.get("/health").json() == {"status": "ok"}
            assert (
                client.get(job["status_url"], headers=HEADERS).json()["status"]
                == "running"
            )
            assert submit(client, job["operation"], job["operation"]).status_code == 200
            other = next(name for name in adapters if name != job["operation"])
            conflict = submit(client, other, job["operation"])
            assert conflict.status_code == 409
            assert conflict.json()["detail"]["code"] == "idempotency_conflict"
            busy = submit(client, other, "new-key")
            assert busy.json()["detail"]["job_id"] == job["job_id"]
            assert len(calls) == 1
        finally:
            release.set()
        assert completed(client, job)["status"] == "succeeded"


def test_same_key_race(tmp_path):
    release = threading.Event()
    calls = []

    def adapter(job_id):
        calls.append(job_id)
        assert release.wait(5)
        return {}

    with TestClient(
        create_app(tmp_path / "jobs.db", {"index_wordpress": adapter})
    ) as client:
        try:
            with ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(submit, client) for _ in range(2)]
                responses = [f.result(timeout=3) for f in futures]
            assert sorted(r.status_code for r in responses) == [200, 202]
            assert len({r.json()["job_id"] for r in responses}) == 1
        finally:
            release.set()
        completed(client, responses[0].json())
        assert len(calls) == 1


def test_failure_safe_and_slot_released(tmp_path, caplog):
    def broken(_job_id):
        raise RuntimeError("SECRET-provider-body")

    with TestClient(
        create_app(
            tmp_path / "jobs.db",
            {
                "index_wordpress": broken,
                "evaluate_retrieval": lambda _: {"ok": True},
            },
        )
    ) as client:
        failed = completed(client, submit(client).json())
        assert failed["status"] == "failed"
        assert failed["result"] is None
        assert failed["error"]["code"] == "operation_failed"
        assert "SECRET" not in json.dumps(failed) + caplog.text
        job = submit(client, "evaluate_retrieval", "next")
        assert job.status_code == 202
        assert completed(client, job.json())["status"] == "succeeded"


@pytest.mark.parametrize(
    "payload",
    [
        {"operation": "shell"},
        {"operation": "index_wordpress", "path": "SECRET"},
        {"operation": "evaluate_retrieval", "rebuild": True},
        {},
        {"operation": 1},
    ],
)
def test_strict_body(tmp_path, payload):
    with TestClient(create_app(tmp_path / "jobs.db", {})) as client:
        response = client.post("/jobs", json=payload, headers=HEADERS)
        assert response.status_code == 422
        assert "SECRET" not in response.text


@pytest.mark.parametrize("key", [None, "", "   ", "x" * 129])
def test_required_bounded_key(tmp_path, key):
    headers = {"X-API-Key": "operations-test"}
    if key is not None:
        headers["Idempotency-Key"] = key
    with TestClient(create_app(tmp_path / "jobs.db", {})) as client:
        assert (
            client.post(
                "/jobs", json={"operation": "index_wordpress"}, headers=headers
            ).status_code
            == 422
        )


@pytest.mark.parametrize("key", [None, "wrong", "public-test"])
def test_authentication(tmp_path, key):
    headers = {"X-API-Key": key} if key else {}
    with TestClient(create_app(tmp_path / "jobs.db", {})) as client:
        assert client.get("/health").status_code == 200
        assert (
            client.post(
                "/jobs", json={"operation": "index_wordpress"}, headers=headers
            ).status_code
            == 401
        )
        assert client.get("/jobs/unknown", headers=headers).status_code == 401


@pytest.mark.parametrize("configured", [None, SecretStr("")])
def test_unconfigured_auth(tmp_path, monkeypatch, configured):
    monkeypatch.setattr(settings, "operations_api_key", configured)
    with TestClient(create_app(tmp_path / "jobs.db", {})) as client:
        assert submit(client).status_code == 503
        assert client.get("/jobs/unknown", headers=HEADERS).status_code == 503


@pytest.mark.parametrize("status", ["queued", "running"])
def test_restart_recovery(tmp_path, status):
    database = tmp_path / "jobs.db"
    runner = Runner(database, {})
    runner.close()
    with sqlite3.connect(database) as db:
        db.execute(
            "INSERT INTO jobs VALUES (?, ?, ?)",
            (
                "interrupted",
                "first",
                json.dumps(
                    {
                        "job_id": "interrupted",
                        "operation": "index_wordpress",
                        "status": status,
                        "result": None,
                    }
                ),
            ),
        )
    with TestClient(create_app(database, {})) as client:
        response = submit(client)
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["error"]["code"] == "runner_interrupted"


def test_second_process_owner_rejected(tmp_path):
    database = tmp_path / "jobs.db"
    runner = Runner(database, {})
    try:
        with pytest.raises(RunnerUnavailable):
            Runner(database, {})
    finally:
        runner.close()


def test_storage_completion_failure_fails_closed(tmp_path, monkeypatch):
    runner = Runner(tmp_path / "jobs.db", {"index_wordpress": lambda _: {}})
    original = runner._save

    def fail_terminal(db, job):
        if job["status"] in ("succeeded", "failed"):
            raise sqlite3.OperationalError("SECRET")
        original(db, job)

    monkeypatch.setattr(runner, "_save", fail_terminal)
    runner.submit("index_wordpress", "first")
    runner._executor.shutdown(wait=True)
    with pytest.raises(RunnerUnavailable):
        runner.submit("index_wordpress", "next")
    runner.close()
    recovered = Runner(tmp_path / "jobs.db", {})
    try:
        job, created = recovered.submit("index_wordpress", "first")
        assert not created
        assert job["error"]["code"] == "runner_interrupted"
    finally:
        recovered.close()


def test_insert_failure_starts_no_work(tmp_path, monkeypatch):
    calls = []
    runner = Runner(tmp_path / "jobs.db", {"index_wordpress": calls.append})
    with sqlite3.connect(tmp_path / "jobs.db") as db:
        db.execute(
            "CREATE TRIGGER reject_insert BEFORE INSERT ON jobs "
            "BEGIN SELECT RAISE(FAIL, 'SECRET'); END"
        )
    try:
        with pytest.raises(RunnerUnavailable):
            runner.submit("index_wordpress", "first")
        assert calls == []
    finally:
        runner.close()
