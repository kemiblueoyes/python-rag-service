# Retrieval quality policy v1

`retrieval-quality-policy.json` defines how you compare a retrieval evaluation
with the approved baseline. `approved-retrieval-baseline.json` records dataset
1.7's initial report, generated at `2026-10-14T01:54:03.845276+00:00`. The
baseline `summary` matches the supplied `retrieval_baseline.json`, stored
unchanged at `evidence/doc-landscape-v1.7-initial-retrieval.json`. The baseline
records that file's SHA-256 digest. Don't replace this baseline after a
successful run, a retry, an improvement, or resolution of a known failure.
Replace it only after an explicit baseline review.

## Verified configuration for dataset 1.7

Operations evaluation job `874d4473-d85c-4dc3-b314-3225ff8755b5` succeeded for
dataset 1.7. `evidence/doc-landscape-v1.7-configuration-job.json` stores the
complete job result, without secrets. The recorded settings match the original
report: collection `rag_chunks`, embedding model `voyage-4-lite`, support
cutoff `0.7`, and `k=5`. Dataset identity and case counts match as well. The
fresh summary equals the original summary, and only `multi-section-001` failed.
The fixed summary still comes from the original retrieval report that was supplied
with the baseline.

The fresh operations job supplies the remaining configuration fields. The
original retrieval report records only collection, embedding model, support cutoff,
and `k`, so it can't establish the other historical values. The verification
job didn't change any settings. When required metadata is missing or the
configuration doesn't match, return `needs_review` before you make a
metric-based quality decision.

## Mount the policy files in Docker n8n

Mount `automation/n8n/policies` read-only into the n8n container so the workflow
can access the policy files. For example, add this entry to the existing n8n
service's Docker Compose `volumes` list, keeping the service's other mounts:

```yaml
volumes:
  - "./automation/n8n/policies:/opt/rag-policies:ro"
```

Recreate the n8n container through its existing deployment procedure so the
mount takes effect. Read and parse these two files from the container:

- `/opt/rag-policies/retrieval-quality-policy.json`
- `/opt/rag-policies/approved-retrieval-baseline.json`

Read them with the deployment's permitted local-file mechanism, then parse the
JSON. Confirm that file-access restrictions allow `/opt/rag-policies`. Without
this mount, the n8n container doesn't include the repository checkout. Load
both files once at the start of each execution, and keep that snapshot for
retries. Check `schema_version`, `policy_version`, and configuration
verification before you compare results. If loading or validation fails, stop
the comparison and report the specific error. Don't record that run as passed.

When you deploy another reviewed version, update the mounted policy and
baseline together, while no new execution can load a partially updated pair.
Keep earlier versions in Git.

The RAG Indexing workflow (`automation/n8n/workflows/rag-indexing-workflow.json`)
loads these policy files, compares retrieval results, and routes confirmed
regressions to Jira. Importing the workflow doesn't verify your deployment
configuration. In your n8n instance, configure and verify the policy-file
mount, runner and Jira credentials, Jira project and issue type, schedule, and
failure-alert workflow.

## Compare retrieval results with the baseline

Normalize runner results and report metadata to the field names in
`retrieval-quality-policy.json`. For runner results, read top-level `k` from
`retrieval_configuration.k`. The stored report already uses top-level `k`. A
command-line report doesn't include the full retrieval configuration. Don't
copy the baseline configuration into that report. Associate the configuration
with the evaluation job that produced the report before you compare.

Use the first matching outcome, in this order: `operational_failure`,
`needs_review`, `quality_failed`, then `passed`. A missing or null required
metric is unavailable, so the outcome is `needs_review`. A supplied non-number,
non-finite value, or value outside the inclusive range 0 to 1 is malformed, so
the outcome is `operational_failure`. When case-count or coverage metadata is
missing, return `needs_review`. When counts or case outcomes contradict each
other, return `operational_failure`. To identify new failures, require either
complete case outcomes (`case_id` and a boolean `passed`) or the runner's
`failed_case_ids` list.

Compare the unrounded decimal values. A metric passes when it meets its minimum
and its maximum decline, including exact equality. Don't round the baseline or
the published metrics. Use decimal-safe comparisons so binary floating-point
subtraction doesn't turn an exact boundary into a failure, and test equality
explicitly. Record every metric breach and every newly failed case. A
maximum-decline breach or a newly failed case qualifies for the Jira regression
route in the RAG Indexing workflow. Configure and verify that integration
before you enable scheduled runs. Include known failure `multi-section-001` in
the outcome when quality passes.

Record these fields in every outcome, as the policy declares:
`indexing_job_id`, `evaluation_job_id`, `n8n_execution_id`, `policy_version`,
`dataset_version`, `report_paths`, and `reasons`. When a context field is
unavailable, leave it null and record a reason. Don't invent an ID.
Comparability doesn't require a corpus fingerprint, because indexing is
expected to change source content. A reviewed change to labels or references
requires a new dataset version and a baseline review.
