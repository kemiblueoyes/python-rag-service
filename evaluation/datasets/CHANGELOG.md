# Baseline dataset changes

## 1.7 — October 13, 2026

Added the reviewed supporting source “What Writers Lose When Ephemeral Knowledge
Disappears” from `wordpress:page:1475`, *Ephemeral Knowledge: The Richest Layer
Nobody Captures*, to `context-001`:
`wordpress:page:1475:chunk:v1:6018ea1a074ee39214353b4a3b87f330c8bda8094ac3568649f260567146c61b`.

The current indexed passage explains why context makes documentation explanatory:
writers need the reasoning behind features to contextualize use cases and help
users understand why an action makes sense. Losing that context produces accurate
but thin documentation. This supports the case's question about the importance
of context, so the reviewed passage is now labeled `supporting` rather than left
unjudged.

Preserved every existing relevant and nonrelevant source, relevance role, and test
expectation. The dataset still contains 22 cases; retrieval settings are unchanged.
No live evaluation was run for this addition.

## 1.6 — October 13, 2026

Refreshed five chunk references for `wordpress:page:2672` (Documentation
Engineering) against the current `data/wordpress-chunks.json`. The indexed source
has a modification timestamp of `2026-10-13T07:20:41`.

Compared with the text preserved in the approved 1.5 retrieval report, the
introductory chunk (empty `heading_path`) adds a space before the period in
`docs-as-code .`; “What the Discipline Spans” adds a space before the comma in
`governance ,`. Chunk identity hashes the document ID, heading path, text, and
chunk-ID version, so these text changes invalidate the previous IDs without
changing the passages' meaning or relevance.

| Chunk | Previous ID | Current ID | References |
| --- | --- | --- | --- |
| Introduction (`[]`) | `wordpress:page:2672:chunk:v1:96a50252ff41f329b6bc8082287c9e2a964e7b6beb98ae19842fe4dff1d2edf5` | `wordpress:page:2672:chunk:v1:c766bea21181124ceef5606d32b1484f1417fede0791f2a1cc94bd744799f60d` | 2 |
| What the Discipline Spans | `wordpress:page:2672:chunk:v1:49ec96efb031a85bcd9176a8ee83effaf23d5de887ab5ab30e1d011da77e5474` | `wordpress:page:2672:chunk:v1:87abbcd779d51ab1efff333a0143c52e07404387664727ce45cd1bc51db7cbf7` | 3 |

Content review confirmed the existing judgments:

- `documentation-engineering-001`: both passages explain that the role designs
  the knowledge system and implements its architecture through operational
  machinery, rather than only producing individual documents.
- `documentation-engineering-002`: both passages define the discipline around
  designing the system content lives in; the spans section details tooling,
  governance, versioning, and lifecycle responsibilities.
- `updated-content-001`: the spans section still connects architectural design
  with operational implementation. The unchanged feedback-loop source in this
  case continues to support the expectation about operational evidence feeding
  back into architecture.

Preserved all explicit and implicit relevance roles, queries, filters, categories,
answer requirements, empty-result expectations, and case notes. Retrieval settings
and the 22-case composition are unchanged. Historical 1.5 dataset/report snapshots
remain unchanged. This reference refresh does not assert a new live evaluation
score; no live retrieval evaluation was run for this change.
