---
name: add-changelog-entry
description: >
  Add a Python RAG Service changelog entry in fern/docs/pages/changelog/
  from pull requests, commits, diffs, or user-provided context. Use for
  release notes and changelog additions following the repository's
  release-note template, rather than ordinary documentation pages.
---

# Add a changelog entry

Create a concise, evidence-backed release note using
`doc-infrastructure/templates/release-note.mdx`. Read the current template
when invoked; do not substitute a generic changelog format or copy an older
entry's structure over the template.

## Establish the change and its evidence

Follow the checkout and preservation instructions in `AGENTS.md`. Verify the
repository path, branch, and existing changes before editing.

Read:

- `doc-infrastructure/README.md` for page creation, generation, and validation.
- `doc-infrastructure/content-model.yml` for metadata and relationship rules.
- `doc-infrastructure/templates/release-note.mdx` for structure.
- The style, technical accuracy, terminology, and Fern platform guides in
  `doc-infrastructure/`.
- Existing entries in `fern/docs/pages/changelog/`, the page registry, and
  relevant navigation in `fern/docs.yml`.

Use the supplied PRs, commits, diffs, or narrative to establish the intended
scope. For PRs, inspect their descriptions, status, and changed code using
available GitHub tools or local evidence. For commits or ranges, inspect the
actual diff and relevant tests, not just commit subjects. Combine overlapping
PR and commit evidence without counting the same change twice. Do not expand
to unrelated recent commits unless the user requests a broader release summary.

Check behavior claims against the relevant implementation at the target
revision. Separate implemented changes from proposed or unmerged work. A merged
PR or commit alone does not prove deployment or establish a release version.
For narrative-only input, draft the supported claims and identify any details
that cannot be verified. Ask only for missing facts that materially affect the
entry, such as an ambiguous release scope, date, or contradictory behavior.
Do not invent version numbers, performance gains, compatibility guarantees,
migration steps, or resolved issues.

Keep a compact mapping of substantive claims to source PRs, commits, files,
or supplied context for the review summary. Public prose should explain user
impact; include source links only where they help readers.

## Choose the entry and metadata

Use `fern/docs/pages/changelog/YYYY-MM-DD.mdx`, following the existing dated
entry convention. Use the supplied release date when available. Otherwise use
the user's current date for a new draft and state that assumption; do not
present it as a verified historical release date. The filename's release date
and the generated `last_modified` date serve different purposes.

Inspect any entry already at that path before writing. Extend it only when it
covers the same release and the requested addition belongs there. Preserve its
ID and existing content. If it represents a different release, resolve the
intended date or grouping with the user rather than overwriting it or inventing
a filename suffix that Fern may not recognize.

Choose a unique stable page ID, a specific title, a brief impact-focused
subtitle, and a searchable description. Set `content_type: release_note` and
include the required `tags`. Select controlled `topics`, `components`, and
`audience` from the content model based on substantive content. Consider
`topic-release-history` when it remains an approved value. Tags are release
labels; do not assume they use the topic vocabulary. Include `version` only
when the change is tied to a verified application version.

For a new file, use the documented `create_doc_page` command with the selected
metadata and path. It creates frontmatter and updates the registry; add the
subtitle, tags, and template body yourself. Do not rerun it for an existing
entry. Start new entries with `lifecycle_status: draft`; preserve the lifecycle
of existing entries unless the requested work calls for changing it. Complete
the requested draft in one pass unless the user requests staged review.

## Write the release note

Start with a short summary of what changed and why it matters. Fern supplies
the H1. Follow the current template's H2 sections and order:

1. **What's changed** — required. Explain new behavior, fixes, or improvements
   in terms of observable user impact. Group related changes; avoid a raw
   commit list. Where useful, describe the previous and new behavior.
2. **Breaking changes** — include only for supported compatibility changes.
3. **Upgrade or migration** — include only when adoption requires action.
   Verify commands, configuration names, defaults, and sequencing.
4. **Known issues** — include only for relevant unresolved limitations or
   workarounds supported by the evidence.
5. **Related documentation** — required. Link to useful existing pages using
   published site paths, with the template's bold linked title and one-sentence
   explanation. Use a bullet list when there is more than one link.

Remove template placeholders and the literal optional markers from headings.
Omit inapplicable optional sections rather than filling them with boilerplate.
Use registered page IDs for `related_pages` and verify that the linked pages
actually explain the changed behavior. Flag stale related documentation in the
handoff without silently expanding into a documentation rewrite. Keep recorded
evaluation results scoped to their specific runs and configurations.

## Integrate and validate

Fern already reads the changelog directory through the changelog tab in
`fern/docs.yml`. Confirm that configuration; do not add an ordinary navigation
entry for each release note.

Regenerate the page registry if it was not already updated by page creation or
if IDs or content types changed. Generate `last_modified` with the documented
command; do not hand-edit generated metadata or registry output. Review generator
diffs for unrelated changes and preserve pre-existing work.

Run the checks documented in `doc-infrastructure/README.md`:

- `npm run lint:docs`
- `uv run python -m rag_service.commands.documentation.validate_docs`

When the user requests a publication-ready entry, resolve outstanding factual
questions, set the completed entry to `published`, and run documentation
validation with `--production`. Drafts may remain for local review but must be
finalized or moved outside the published pages directory before merging, as
specified in the repository guide. Do not equate lifecycle metadata with an
actual deployment.

Resolve failures introduced by the change and report any remaining failures or
checks unavailable in the environment. Inspect Git status and diff in the
intended checkout. Leave changes unstaged and uncommitted unless requested
otherwise. Report the checkout, branch, changed files, source scope, date
assumptions, validation results, and any unresolved evidence gaps.
