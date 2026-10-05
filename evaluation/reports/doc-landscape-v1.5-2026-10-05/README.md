# Doc Landscape evaluation snapshot: dataset 1.5

This snapshot set accompanies **Recorded evaluation results**. It preserves the
uploaded report bytes under their canonical filenames and includes the matching
dataset from the repository.

| Artifact | Recorded time (UTC) |
| --- | --- |
| Retrieval baseline | 2026-10-03T18:41:27.536137+00:00 |
| Answer baseline | 2026-08-28T06:10:50.734440+00:00 |
| Human review | 2026-08-28T06:20:00+00:00 |

All three use dataset `doc-landscape-baseline`, version `1.5`. The human review
matches the August 28 answer run. The retrieval and answer evaluations are
separate runs.

- Read the Markdown reports for case results and source evidence.
- Read the JSON files for exact values and programmatic comparisons.
- Read `baseline.json` for queries, filters, source judgments, and answer expectations.

The reports don't record an implementation commit or every retrieval setting.
This set doesn't contain the full historical corpus or Qdrant index.

Keep the published files unchanged. Store later evaluations in a new snapshot
directory, and retain the matching answer report whenever publishing a human review.
