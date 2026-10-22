# ADR-005: External orchestration and a separate local HTTP runner

Status: Accepted for Phase 13 Step 4 (October 12, 2026).

## Decision

Python retains all indexing, retrieval, evaluation, and generation logic.
Optional n8n orchestrates future schedules, triggers, polling, notifications,
and issue creation; it does not own RAG logic or become a core dependency.
Free self-hosted n8n runs in Docker Desktop while Python runs in the existing
local project environment.

A separate FastAPI app, `rag_service.operations.app:app`, listens on port 8001.
The public search/answer API retains its existing app, port, and routes. The
runner calls fixed Python adapters for `index_wordpress` (incremental only) and
`evaluate_retrieval`, using configured sources and artifact paths.

- `GET /health`: unauthenticated runner/store availability, not provider health.
- `POST /jobs`: authenticate with the separate secret `OPERATIONS_API_KEY` via
  `X-API-Key`; require a bounded nonblank `Idempotency-Key` and strict operation
  input. Return 202 for acceptance, 200 for the existing same-key submission,
  or 409 for conflicting reuse or another active job, including its job ID.
- `GET /jobs/{job_id}`: authenticated polling of timestamps, status, safe result
  metadata or controlled failure. Unknown IDs return 404. Failed jobs return 200
  as retrieved records, with `status: failed`.

Missing key configuration returns 503 and starts no work. Missing/invalid client
keys return 401. Public API startup does not require the operations key.

One process and one background worker serve both operations. Submission reserves
one shared slot atomically; there is no unbounded queue, Redis, or Celery. SQLite
under `data/operations/` retains job outcomes and idempotency keys across restarts.
A local process lock prevents simultaneous owners of the same database. The
thread is not a durable queue. Graceful shutdown waits for work; restart marks
unfinished records failed with `runner_interrupted`, without silently resuming.
Unrecoverable outcome-persistence failures make the runner unavailable until
storage repair and restart, rather than reporting false success.

Evaluation constructs a fresh retrieval service and writes reports under
`data/operations/runs/{job_id}/`. CLI reports remain at their local defaults;
the approved baseline is preserved. Execution success is separate from quality:
failed cases do not fail an otherwise valid completed evaluation. No new quality
threshold is introduced.

## Alternatives considered

- Add administrative routes or scheduling to the public Python API.
- Use cron/GitHub Actions/cloud scheduling only.
- Put ingestion or evaluation logic in n8n.
- Introduce a distributed task queue for this local first step.

## Rationale and consequences

The authenticated HTTP boundary supports Docker-host connectivity while keeping
orchestration replaceable and RAG behavior in Python. It adds a separately managed
local process, credential, SQLite store, and report history. Use one Uvicorn worker
and avoid reload while jobs run. Do not run manual CLI indexing concurrently.
Schedules, evaluation chaining, quality routing, Slack/email, and Jira are deferred.

The public API's cached BM25 retriever still needs a refresh after indexing.
Indexing publishes the chunk file and then the document checkpoint with an
atomic replace. A failed publication leaves that checkpoint unchanged, so the
next run still reports the pending changes. This runner does not refresh the
public API's BM25 index.

See the [local runner guide](../../operations/README.md) for startup, Docker
connectivity, submission and polling commands, and recovery details. This guide
is separate from the public search/answer API reference.
