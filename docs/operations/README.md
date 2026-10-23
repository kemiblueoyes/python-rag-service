# Local operations runner

Run indexing and retrieval evaluation through a separate authenticated HTTP app.
The public search/answer app and its routes are unchanged. n8n is optional.

## Setup

Run commands from the checkout containing this implementation. Keep the existing
WordPress, Voyage, Qdrant, and retrieval settings in its local `.env` file.
Set a separate `OPERATIONS_API_KEY` there; do not reuse `RAG_API_KEY`.
Both keys are optional at public API startup. The operations job endpoints return
503 and start no work if their key is missing or empty, or 401 for a missing or
incorrect client key. Never commit `.env` or a real key.

Start from the project root:

```bash
uv run uvicorn rag_service.operations.app:app --host 127.0.0.1 --port 8001
```

Use one Uvicorn process and one worker, without `--reload`. The runner also holds
an exclusive local file lock on its database for its lifetime, preventing another
runner using the same database from recovering a live job. This uses POSIX file
locking (macOS/Linux); keep the database on the local filesystem.
Do not run manual indexing/evaluation commands concurrently with runner jobs;
the reservation only coordinates jobs submitted to this runner.

## Manual verification

In another terminal at the same project root, load the key into an environment
variable without printing it. This reads `.env` through the existing settings loader:

```bash
export OPERATIONS_API_KEY="$(uv run python -c 'from rag_service.config import settings; print(settings.operations_api_key.get_secret_value() if settings.operations_api_key else "")')"
RUNNER_URL=http://127.0.0.1:8001
curl -fsS "$RUNNER_URL/health" | python3 -m json.tool
```

Health returns `{"status": "ok"}` when the runner and job store are available.
It does not check WordPress, Voyage, Qdrant, or retrieval quality.

Submit incremental indexing, save the actual response, and poll its actual job ID:

```bash
IDEMPOTENCY_KEY="$(python3 -c 'import uuid; print(uuid.uuid4())')"
SUBMISSION="$(curl -fsS "$RUNNER_URL/jobs" \
  -H "X-API-Key: $OPERATIONS_API_KEY" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"operation":"index_wordpress"}')"
printf '%s\n' "$SUBMISSION" | python3 -m json.tool
JOB_ID="$(printf '%s' "$SUBMISSION" | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')"
curl -fsS "$RUNNER_URL/jobs/$JOB_ID" \
  -H "X-API-Key: $OPERATIONS_API_KEY" | python3 -m json.tool
```

Repeat the polling command until `status` is `succeeded` or `failed`.
A new submission returns 202 immediately with an initial queued/running status,
job ID, and relative `status_url`. It does not mean the work completed.
An identical key and operation returns the existing job with 200, including after
completion or restart. Preserve the key when retrying an uncertain submission.
Use a fresh key for every new intended run. Keys must be nonblank and at most 128
characters. Reusing a key for another operation returns 409. A different request
while a job is active returns 409 with the active job ID; there is no waiting queue.
Unknown jobs return 404. Polling a failed job returns 200 with `status: failed`,
a controlled error code/message, and no successful result.

After indexing finishes, submit evaluation with a fresh key:

```bash
IDEMPOTENCY_KEY="$(python3 -c 'import uuid; print(uuid.uuid4())')"
SUBMISSION="$(curl -fsS "$RUNNER_URL/jobs" \
  -H "X-API-Key: $OPERATIONS_API_KEY" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"operation":"evaluate_retrieval"}')"
printf '%s\n' "$SUBMISSION" | python3 -m json.tool
JOB_ID="$(printf '%s' "$SUBMISSION" | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')"
curl -fsS "$RUNNER_URL/jobs/$JOB_ID" \
  -H "X-API-Key: $OPERATIONS_API_KEY" | python3 -m json.tool
```

These are the only supported operations. Extra fields, including paths, source
URLs, provider settings, shell commands, and rebuild flags, are rejected.

## Outcomes and recovery

Job records persist in `data/operations/jobs.sqlite3`. Each evaluation creates a
fresh retrieval service and writes `retrieval_baseline.json` and
`retrieval_baseline.md` under `data/operations/runs/{job_id}/`. Its status result
contains this run's summary, failed case IDs, report paths, dataset identity,
generation time, and non-secret retrieval configuration. Nullable metrics remain
null. Full case text stays in the report files, not in HTTP job results.
The CLI continues writing to `data/evaluation/latest/`; the approved baseline is
not overwritten by runner jobs.

Indexing uses normal incremental synchronization. Vector synchronization
finishes before either JSON file is published. Each file is written to a
temporary file in its destination directory, flushed, and fsynced, then moved
into place with an atomic replace, so readers never see partially written JSON.
A failed publication removes its temporary file. The chunk file
(`LEXICAL_CORPUS_PATH`, default `data/wordpress-chunks.json`) is published
first. `data/wordpress-documents.json` is published last and is the checkpoint
for a completed run. The job result still includes change counts,
indexed/cleared counts, `changes_detected`, and artifact paths.

If vector synchronization fails, both existing files stay as they were and the
next run retries the same changes. If chunk publication fails, the document
checkpoint stays unchanged. If document publication fails after the chunk file
is in place, both destinations remain readable JSON: the chunk file can already
hold the new corpus, and the checkpoint is still the previous run. The next run
compares WordPress with that checkpoint, so it still detects and reports the
pending changes. A later successful job therefore still has `changes_detected`
when content changed, and n8n can continue to evaluation. A forced stop between
the two replaces leaves that same recoverable pair. A killed process can leave
a hidden temporary file beside the destination. The next run reads the destination files.

Job success means execution and report/artifact writes finished. It does not
impose a quality threshold. The October 12 verified baseline had 22 cases,
95.5% overall success, and failing case `multi-section-001`; all 14 answerable
cases had a primary hit and all 8 unanswerable cases returned no results.
Such an evaluation is still a successful execution. Provider, evaluator, or
report-write failures produce failed jobs, never an older report's result.

The worker is an in-process thread, not a durable queue. Graceful shutdown stops
accepting work and waits for the worker to finish and close its clients. Forced
termination can interrupt work. At the next startup, queued/running records are
marked failed with `runner_interrupted`; they are not retried automatically.
Review the outcome before submitting a new key: external writes might have
occurred before the interruption. If terminal persistence fails, the runner
attempts to record `storage_failed`; if even that write fails, it stops serving
jobs/health successfully and retains its reservation until restart recovery.
Fix the local storage problem before restarting. Retain the database and report
files for polling history; there is no automatic retention cleanup in this step.

## n8n in Docker Desktop

Use `http://host.docker.internal:8001` in n8n HTTP requests. Verify `/health`
from inside Docker first. If the loopback listener is unreachable, restart with
an appropriate Docker-reachable address, for example `--host 0.0.0.0`, with
local firewall rules restricting access. Keep the separate key in n8n credentials,
send it as `X-API-Key`, and preserve the idempotency key for submission retries.
Poll the returned `status_url` using the runner base URL.

The workflow in `automation/n8n/workflows/index-wordpress.json` includes manual
and scheduled triggers, indexing submission and polling, evaluation chaining when
content changes, retrieval-quality policy comparison, and Jira regression routing.
The Jira route finds or creates an open regression issue and records new job
findings without repeating an already recorded job. Workflow failures use explicit
error branches. Keep runner credentials, Jira credentials, and the policy-file
mount configured in n8n; the runner itself does not install or schedule workflows.
See `automation/n8n/policies/README.md` for the policy files and Docker mount.

## Public API lexical refresh

Keep the public API and operations runner as separate processes with access to the
same configured `LEXICAL_CORPUS_PATH`. After indexing atomically replaces that
file, each API process detects the change on its next search or answer request
and builds a complete replacement BM25 index before using it. No API restart is
required after indexing. Initialization remains lazy, and unchanged files reuse
the existing in-memory index.

Refresh and lexical searches are serialized within each API process. Requests
wait for a rebuild, while a search already using the previous snapshot can finish
with it. Refresh replaces only the in-memory lexical index; it does not replace
or close provider clients. A missing, unreadable, invalid, or continuously changing
corpus returns the existing controlled `configuration_error` response instead of
serving stale lexical results. Later requests retry and recover once a valid
corpus is available.

Each API worker refreshes independently using file identity and metadata checks;
there is no background watcher. Qdrant updates and corpus publication are not one
transaction, so requests during indexing can observe different vector and lexical
generations. Environment configuration changes still require a process restart.
