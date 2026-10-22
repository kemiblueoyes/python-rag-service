"""Single-process worker with persisted outcomes, not a durable task queue."""

import fcntl
import json
import logging
import sqlite3
import threading
from collections.abc import Callable, Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

Adapter = Callable[[str], dict[str, Any]]
logger = logging.getLogger(__name__)

MESSAGES = {
    "operation_failed": (
        "The operation failed. Check local configuration and diagnostics."
    ),
    "runner_interrupted": "The runner stopped before recording a completed outcome.",
    "storage_failed": "The runner could not persist the operation outcome.",
    "dispatch_failed": "The runner could not start the operation.",
}


class RunnerUnavailable(RuntimeError):
    """The runner cannot safely accept or report work."""


class JobConflict(RuntimeError):
    def __init__(self, code: str, job_id: str) -> None:
        self.code = code
        self.job_id = job_id


def now() -> str:
    return datetime.now(UTC).isoformat()


def failure(code: str) -> dict[str, str]:
    return {"code": code, "message": MESSAGES[code]}


def diagnostic(job: dict[str, Any], reason: str) -> None:
    logger.info(
        "job_id=%s state=%s",
        job["job_id"],
        job["status"],
        extra={"operation": job["operation"], "reason": reason},
    )


class Runner:
    def __init__(self, database: Path, adapters: Mapping[str, Adapter]) -> None:
        self._lock = threading.Lock()
        self._adapters = adapters
        self._database = database
        self._active: str | None = None
        self._available = True
        self._closed = False
        database.parent.mkdir(parents=True, exist_ok=True)
        self._lease = database.with_suffix(".lock").open("a")
        try:
            # A second server must not recover records owned by a live worker.
            fcntl.flock(self._lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self._connection() as db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS jobs ("
                    "job_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL, "
                    "record TEXT NOT NULL)"
                )
                for row in db.execute("SELECT record FROM jobs").fetchall():
                    job = json.loads(row[0])
                    if job["status"] in ("queued", "running"):
                        job.update(
                            status="failed",
                            completed_at=now(),
                            error=failure("runner_interrupted"),
                        )
                        self._save(db, job)
                        diagnostic(job, "runner_interrupted")
            self._executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="operations"
            )
        except Exception:
            self._lease.close()
            raise RunnerUnavailable() from None

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self._database, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _save(self, db: sqlite3.Connection, job: dict[str, Any]) -> None:
        cursor = db.execute(
            "UPDATE jobs SET record=? WHERE job_id=?",
            (json.dumps(job, allow_nan=False), job["job_id"]),
        )
        if cursor.rowcount != 1:
            raise RunnerUnavailable()

    def _check(self) -> None:
        if not self._available or self._closed:
            raise RunnerUnavailable()

    def health(self) -> None:
        with self._lock:
            self._check()
            try:
                with self._connection() as db:
                    db.execute("SELECT job_id FROM jobs LIMIT 1").fetchall()
            except Exception:
                raise RunnerUnavailable() from None

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._check()
            try:
                with self._connection() as db:
                    row = db.execute(
                        "SELECT record FROM jobs WHERE job_id=?", (job_id,)
                    ).fetchone()
                    return json.loads(row[0]) if row else None
            except Exception:
                raise RunnerUnavailable() from None

    def submit(self, operation: str, key: str) -> tuple[dict[str, Any], bool]:
        with self._lock:
            self._check()
            try:
                with self._connection() as db:
                    row = db.execute(
                        "SELECT record FROM jobs WHERE idempotency_key=?", (key,)
                    ).fetchone()
                    if row:
                        existing = json.loads(row[0])
                        if existing["operation"] != operation:
                            raise JobConflict(
                                "idempotency_conflict", existing["job_id"]
                            )
                        return existing, False
                    if self._active:
                        raise JobConflict("runner_busy", self._active)
                    job_id = str(uuid4())
                    job = {
                        "job_id": job_id,
                        "operation": operation,
                        "status": "queued",
                        "status_url": f"/jobs/{job_id}",
                        "created_at": now(),
                        "started_at": None,
                        "completed_at": None,
                        "result": None,
                        "error": None,
                    }
                    db.execute(
                        "INSERT INTO jobs VALUES (?, ?, ?)",
                        (job_id, key, json.dumps(job)),
                    )
                self._active = job_id
                diagnostic(job, "accepted")
                try:
                    self._executor.submit(self._execute, job.copy())
                except Exception:
                    self._finish(job, None, "dispatch_failed")
                    raise RunnerUnavailable() from None
                return job, True
            except (JobConflict, RunnerUnavailable):
                raise
            except Exception:
                raise RunnerUnavailable() from None

    def _execute(self, job: dict[str, Any]) -> None:
        try:
            with self._lock:
                job.update(status="running", started_at=now())
                with self._connection() as db:
                    self._save(db, job)
                diagnostic(job, "started")
        except Exception:
            with self._lock:
                self._finish(job, None, "storage_failed")
            return
        try:
            result = self._adapters[job["operation"]](job["job_id"])
            # Validate serializability before marking execution successful.
            json.dumps(result, allow_nan=False)
        except Exception:
            with self._lock:
                self._finish(job, None, "operation_failed")
        else:
            with self._lock:
                self._finish(job, result, None)

    def _finish(
        self, job: dict[str, Any], result: dict[str, Any] | None, code: str | None
    ) -> None:
        job.update(
            status="failed" if code else "succeeded",
            completed_at=now(),
            result=result,
            error=failure(code) if code else None,
        )
        try:
            with self._connection() as db:
                self._save(db, job)
        except Exception:
            code = "storage_failed"
            job.update(status="failed", result=None, error=failure(code))
            try:
                with self._connection() as db:
                    self._save(db, job)
            except Exception:
                # Keep the reservation and fail closed until restart recovery.
                self._available = False
                diagnostic(job, "storage_failed")
                return
        self._active = None
        diagnostic(job, code or "completed")

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=True)
        self._lease.close()
