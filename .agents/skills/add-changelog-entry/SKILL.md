---
name: add-changelog-entry
description: >
  Add a Python RAG Service changelog entry in fern/docs/pages/changelog/
  from pull requests, commits, diffs, or user-provided context. Use for
  release notes and changelog additions following the repository's
  release-note template, rather than ordinary documentation pages.
---

# Add a changelog entry

Create a concise, evidence-backed release note that follows the repository's
release-note template and documentation style guide.

Include changes that affect consumers of the Python RAG Service or significantly
improve their documentation experience. Exclude internal documentation tooling, agent skills,
authoring workflows, and infrastructure changes unless they directly affect users.

## Step 1: Review repository instructions and guides

Follow `AGENTS.md`. Verify the repository path, branch, and existing changes
before editing. Preserve pre-existing work.

Read the current versions of:

- `doc-infrastructure/README.md` for page creation, generation, and validation.
- `doc-infrastructure/content-model.yml` for metadata and relationship rules.
- `doc-infrastructure/templates/release-note.mdx` for structure.
- The style guide (`style-guide`), technical accuracy, terminology, and Fern
  platform guides in `doc-infrastructure/`.
- Existing changelog entries, the page registry, and the changelog configuration
  in `fern/docs.yml`.

Read the full style guide before drafting. Apply its applicable rules to the
frontmatter text, headings, body, lists, links, and terminology. Use existing
entries for context, not as substitutes for the template or style guide. If
required guidance is missing or inaccessible, report the blocker rather than
silently substituting generic guidance.

## Step 2: Establish the change and its evidence

Use the supplied PRs, commits, diffs, or narrative to establish the scope.
Inspect PR descriptions, status, changed code, and relevant tests, or the
actual commit diff. Deduplicate overlapping evidence and exclude unrelated
changes unless the user requests a broader release summary.

Verify behavior against the implementation at the target revision. Distinguish
implemented changes from proposed work. A merged PR or commit does not prove
deployment or establish a release version.

For narrative-only input, use supported claims and flag unverified details.
Ask only for missing facts that materially affect the entry. Do not invent
versions, performance gains, compatibility guarantees, migration steps, or
resolved issues. Keep a compact mapping of substantive claims to evidence for
the review summary.

## Step 3: Choose the entry and metadata

Use `fern/docs/pages/changelog/YYYY-MM-DD.mdx`. Use the supplied release date
or, for a new draft, the user's current date and disclose that assumption.
The release date and generated `last_modified` date serve different purposes.

Inspect any existing entry at that path. Extend it only if it covers the same
release, preserving its ID and unrelated content. If it covers a different
release, clarify the date or grouping rather than overwriting it.

Choose a unique stable page ID, specific title, brief impact-focused subtitle,
and searchable description. Set `content_type: release_note` and include the
required `tags`. Select `topics`, `components`, and `audience` from the content
model. Consider `topic-release-history` if approved. Tags are release labels,
not necessarily topic values. Include `version` only if verified.

For a new entry, use the documented `create_doc_page` command to create the
frontmatter and update the registry. Add the subtitle, tags, and template body.
Do not rerun the command for an existing entry. Set new entries to
`lifecycle_status: draft` and preserve the lifecycle status of existing entries
unless a status change is requested and approved in Step 6.

## Step 4: Write the release note

Follow the current release-note template and apply the style guide throughout
writing. Start with a short summary of what changed and why it matters. Fern
supplies the H1. Use the template's H2 sections in order:

1. **What's changed** — required. Explain observable user impact. Group related
   changes rather than listing commits. Contrast previous and new behavior
   where useful.
2. **Breaking changes** — include only verified compatibility changes.
3. **Upgrade or migration** — include only when users must take action. Verify
   commands, configuration names, defaults, and sequencing.
4. **Known issues** — include only supported unresolved limitations or
   workarounds.
5. **Related documentation** — required. Use published site paths, bold linked
   titles, and one-sentence explanations. Use a list for multiple links.

Remove placeholders and optional markers. Omit inapplicable sections. Use
registered page IDs for `related_pages` and verify related links. Flag stale
related documentation without expanding the task into a documentation rewrite.
Keep evaluation results scoped to the specific runs and configurations. Include
source links in public prose only where useful to readers.

## Step 5: Review and validate the draft

Re-read the style guide and review the written entry against its applicable
rules. Correct violations before presenting the entry for review. Do not rely
on linting alone to establish style-guide compliance.

Check technical claims against the evidence, and verify template structure,
metadata, and related links.

Confirm the changelog configuration in `fern/docs.yml`. Do not add an ordinary
navigation entry for each release note. Regenerate the registry if needed and
generate `last_modified` using the documented commands. Do not hand-edit
generated output. Inspect generator diffs for unrelated changes.

Run:

- `npm run lint:docs`
- `uv run python -m rag_service.commands.documentation.validate_docs`

Fix failures introduced by the change. Inspect Git status and diff. Report the
checkout, branch, changed files, source scope, date assumptions, style-guide
review, validation results, and any unresolved evidence gaps or unavailable
checks. Leave changes unstaged and uncommitted unless requested otherwise.

## Step 6: Obtain approval and finalize

Present the reviewed entry and ask the user to approve it for publication.
Keep new entries in `draft` until the user approves. If revisions are requested,
make them and repeat Step 5 before requesting approval again.

After approval, resolve any outstanding factual or validation issues, set
`lifecycle_status: published`, regenerate metadata as required by the repository
guide, and run:

- `uv run python -m rag_service.commands.documentation.validate_docs --production`

Report the final lifecycle status and validation results. Do not report the
entry as publication-ready if production validation fails. Drafts must be
finalized or moved outside the published pages directory before merging, as
specified in the repository guide. A `published` lifecycle status does not
mean the entry has been deployed.
