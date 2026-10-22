# Retrieval quality policy v1

`retrieval-quality-policy.json` declares the comparison contract.
`approved-retrieval-baseline.json` fixes dataset 1.7's initial report, generated at
`2026-10-14T01:54:03.845276+00:00`. Its summary is copied exactly from the supplied
`retrieval_baseline(5).json`, preserved byte-for-byte under `evidence/` with a
SHA-256 digest. Successful runs, retries, improvements, and resolution of known
failures must never overwrite this baseline.

## Configuration verification

Operations evaluation `874d4473-d85c-4dc3-b314-3225ff8755b5` succeeded in this
worktree on October 14, 2026, using dataset 1.7. Its complete non-secret job result
is preserved in `evidence/doc-landscape-v1.7-configuration-job.json`.
The configuration matches every setting recorded by the original report:
collection `rag_chunks`, embedding model `voyage-4-lite`, cutoff `0.7`, and `k=5`.
Dataset identity and case counts also match. The fresh summary happens to equal
the original summary, with only `multi-section-001` failed; the fixed summary's
source remains the original attachment.

The remaining configuration fields come from this fresh operations job, not from
the historical attachment. That attachment cannot prove those historical values.
No settings were changed. Future missing metadata or configuration mismatches
must produce `needs_review` before any metric-based quality decision.

## Delivering the files to Docker n8n

Use a read-only bind mount of this directory. For example, add this entry to the
existing n8n service's Docker Compose `volumes` list, preserving its other mounts:

```yaml
volumes:
  - "/Users/abionta/.codex/worktrees/dd7a/python-rag-service/automation/n8n/policies:/opt/rag-policies:ro"
```

Recreate the n8n container through its existing deployment procedure to apply
the mount. The workflow must read and parse these two files from the container:

- `/opt/rag-policies/retrieval-quality-policy.json`
- `/opt/rag-policies/approved-retrieval-baseline.json`

Use the deployment's permitted local-file reading mechanism, then JSON parsing;
verify file-access restrictions permit `/opt/rag-policies`. Docker cannot see the
host checkout without this explicit mount. Load both files once at the beginning
of each execution and retain that snapshot for retries. Check `schema_version`,
`policy_version`, and configuration verification before comparing. If loading or
validation fails, stop comparison and report the specific error rather than pass.
When deploying another reviewed version, update the mounted files together while
no new execution can load a partially updated pair. Retain prior versions in Git.

This change creates policy data and evidence only. It does not modify the Docker
configuration, n8n workflow, or activate automatic comparisons. Workflow integration
and the Step 8 routing checks remain necessary. The proposed mount is the chosen
delivery method, not a claim that it is already installed.

## Consumer rules

Normalize runner results and report metadata to the field names in the policy.
For runner results, obtain top-level `k` from `retrieval_configuration.k`; the
stored report uses top-level `k`. A CLI report alone lacks full configuration and
must not silently inherit the baseline's configuration. Associate configuration
with the actual evaluation job before comparison.

Apply outcome precedence: operational failure, needs review, quality failed,
passed. A missing/null required metric is unavailable (`needs_review`); a supplied
non-number, non-finite value, or value outside [0, 1] is malformed
(`operational_failure`). Missing case-count/coverage metadata needs review;
contradictory counts or case outcomes are malformed. Require either complete case
outcomes or the runner's explicit failed-case list to identify new failures.

Compare unrounded decimal values. Both absolute floors and maximum declines must
pass, including equality. Do not round the baseline or published metrics. In
particular, binary floating-point subtraction must not turn an exact boundary into
a failure; implement decimal-safe comparisons and test equality explicitly.
Record all metric breaches and newly failed cases. A decline breach or new case
qualifies for the planned Jira regression route; no Jira integration is installed.
Known failure `multi-section-001` remains visible even when quality passes.

Retain indexing/evaluation job IDs, n8n execution ID, policy/dataset versions,
report paths, and specific reasons in every outcome, as declared in the policy.
An unavailable context field remains null with a reason. Never invent an ID.
No corpus fingerprint is required for comparability: indexing is expected to
change source content. Reviewed label/reference changes require a new dataset
version and baseline review.
