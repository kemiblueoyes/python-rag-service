# Maintain the documentation

Use this guide to choose a documentation workflow, find the project standards,
and prepare changes for review and publication. Run commands from the repository
root. Links in this README are relative to `doc-infrastructure/`.

## Choose a workflow

| What you need to do | Start here |
| --- | --- |
| Create a guide, tutorial, explanation, or reference page | [Create a page](#create-a-page) |
| Correct or extend an existing page | [Update an existing page](#update-an-existing-page) |
| Document a release or user-facing change | [Add a changelog entry](#add-a-changelog-entry) |
| Define a term or review glossary coverage for a feature | [Update terminology and the glossary](#update-terminology-and-the-glossary) |
| Check documentation after a code or configuration change | [Review drift](#review-drift-docs-sync-audit) |
| Refresh generated documentation | [Regenerate derived files](#regenerate-derived-files) |
| Preview diagrams and pages | [Preview the site](#preview-the-site) |
| Check publication readiness | [Validate changes](#validate-changes), then [Publish and verify](#publish-and-verify) |

## Find the standards and sources

Use the documentation map in [AGENTS.md](../AGENTS.md) to locate implementation
and tests for the behavior being documented. Existing prose provides context;
verify behavior claims against the relevant implementation or recorded evidence.

### Writing and page design

- [Content model](content-model.yml): content types, required metadata,
  controlled vocabularies, and guidance for selecting page relationships.
- [Style guide](style-guide.md): structure, voice, readability, cross-references,
  acronyms, diagrams, and editorial review.
- [Technical accuracy rules](technical-accuracy-rules.md): verification of
  behavior, examples, configuration, limitations, and evaluation results.
- [Terminology](terminology.md): preferred names and distinctions between
  concepts, including operations and automation.
- [Fern platform rules](fern-platform-rules.md): MDX, links, components, and
  navigation conventions.
- [Templates](templates/): content-type structures used when authoring pages.
  The files in [test-templates](templates/test-templates/) are validator fixtures,
  not alternative authoring templates or published pages.

### Content and configuration

| Location | Purpose |
| --- | --- |
| [Page sources](../fern/docs/pages/) | Authored MDX, changelog entries, and the generated glossary |
| [Site configuration](../fern/docs.yml) | Navigation, URLs, tabs, branding, and publishing instance |
| [Shared snippets](../fern/docs/snippets/) | Reusable content included by pages |
| [Page registry](page-registry.yml) | Generated page IDs and content types for metadata relationships |
| [Glossary source](../docs/data/glossary.yml) | Definitions, examples, aliases, and related terms |
| [OpenAPI specification](../fern/openapi.yml) | Generated API contract used by Fern |
| [Vale styles](../styles/) and [configuration](../.vale.ini) | Automated prose and terminology checks |
| [Mermaid palette](diagram-styles/mermaid-theme.json) | Shared flowchart class colors |
| [Site CSS](../fern/styles.css) | Site presentation, including Mermaid styling |
| [Documentation commands](../src/rag_service/commands/documentation/) | Page initialization, metadata, registry generation, and validation |

## Work with an agent

The repository skills live in [.agents/skills](../.agents/skills/). Their
`SKILL.md` files define the current workflow and approval checkpoints. The
commands and source ownership described here apply whether you work manually
or with an agent.

### Create new pages: author-doc-page

Use [author-doc-page](../.agents/skills/author-doc-page/SKILL.md) for a new page,
including a page already initialized with frontmatter only. It does not apply
to updates to existing authored documentation.

The skill proceeds through outline, draft, final draft, and metadata and
relationship finalization. It requests approval at the checkpoints defined in
the skill. Pages remain `draft` through final-draft review, then move to `review`;
final approval moves them to `published` and triggers production validation.
It also requests approval before changing relationships on other pages.

### Review drift: docs-sync-audit

Use [docs-sync-audit](../.agents/skills/docs-sync-audit/SKILL.md) to compare docs
with a feature, PR, branch, release, API, configuration, command, or repository
area. It reports evidence from both documentation and implementation and states
coverage limits. The audit is read-only unless updates are requested.

### Maintain definitions: update-glossary

Use [update-glossary](../.agents/skills/update-glossary/SKILL.md) for named terms
or a feature area that may need glossary additions or revisions. It reviews
terminology, existing definitions, documentation, and relevant implementation;
then presents proposed YAML entries and terminology issues together for review.
It applies only approved entries and runs the glossary generator and checks.

### Document releases: add-changelog-entry

Use [add-changelog-entry](../.agents/skills/add-changelog-entry/SKILL.md) for
release notes based on PRs, commits, diffs, or supplied context. It follows the
release-note template, verifies user-facing claims, and normally completes a
draft in one pass unless staged review is requested. Publication-ready entries
also require production validation. It does not invent release versions or
assume that merged code has been deployed.

### Use a prompt for a narrower task

The [prompts directory](prompts/) provides helpers without the skills' staged
workflows. These prompts are transitional and will eventually be replaced
entirely by skills. Use an existing skill when it covers the task.

The current prompts are:

- [Author documentation](prompts/author-doc-page.md): create or substantially
  update a page using supplied metadata, a template, and product sources.
- [Review documentation style](prompts/review-doc-style.md): advisory review of
  clarity, audience fit, technical depth, duplication, and unsupported claims.
- [Input lists](prompts/copy-paste-inputs.md): prepare context for those prompts.

Provide the page goal, relevant source material, template, and metadata requested
by the prompt. Review the result and run the applicable checks; prompts do not
replace technical verification or validation.

## Set up the tools

Use a Git checkout with history available; date generation reads that history.
Match the versions installed by [CI](../.github/workflows/ci.yml): Python 3.12,
Node.js 22, the pinned Fern CLI, and Vale 3.22.0. Install uv and npm, then run:

```bash
uv sync --dev --locked
npm ci
FERN_VERSION=$(node -p "require('./fern/fern.config.json').version")
npm install -g "fern-api@${FERN_VERSION}"
```

Install Vale from the [Vale 3.22.0 release](https://github.com/vale-cli/vale/releases/tag/v3.22.0)
and confirm `vale --version`. The repository includes its Microsoft and project
styles. Local Fern preview also uses pnpm; make it available on your `PATH`.

`npm test` is a placeholder that fails. Use the named documentation checks in
[Validate changes](#validate-changes).

## Create a page

This section explains what a new page needs, how to choose its template, and how
to create and connect it to the documentation site. Use it to understand the
process or create a page manually; for guided authoring with review checkpoints,
use the [author-doc-page skill](../.agents/skills/author-doc-page/SKILL.md).

### Choose the purpose and template

Check navigation and existing coverage before adding a page. Establish its
reader goal, stable ID, content type, audience, and relevant product sources.
Use the content model to select metadata based on substantive coverage, not
passing mentions. Distinguish prerequisites, next steps, and related reading.

| Content type | Template |
| --- | --- |
| `overview` | [Overview](templates/overview.mdx) |
| `how_to` | [How-to](templates/how-to.mdx) |
| `tutorial` | [Tutorial](templates/tutorial.mdx) |
| `explanation` | [Explanation](templates/explanation.mdx) |
| `general_reference` | [General reference](templates/general-reference.mdx) |
| `eval_results` | [Evaluation results](templates/evaluation-results.mdx) |
| `release_note` | [Release note](templates/release-note.mdx) |

API endpoint reference pages come from OpenAPI. Glossary entries come from
YAML; [glossary-term.mdx](templates/glossary-term.mdx) illustrates their display
structure rather than serving as a page to edit directly.

### Initialize the page

Create the page and add basic metadata. Adapt this example to the selected metadata:

```bash
uv run python -m rag_service.commands.documentation.create_doc_page \
  --id ExampleGuide \
  --title "Example documentation page" \
  --description "Explain the planned topic and its purpose." \
  --content-type explanation \
  --topics topic-architecture \
  --audience primary \
  --path fern/docs/pages/architecture/example-documentation-page.mdx
```

This creates frontmatter with `lifecycle_status: draft` and updates the page
registry. It does not insert a subtitle, date, template body, or navigation entry.
It rejects existing files, reused IDs, unsupported controlled values, and paths
outside `fern/docs/pages/`. Filenames use lowercase kebab-case and `.mdx`.

Optional flags include `--components`, `--prerequisites`, `--next-steps`, and
`--related-pages`. List flags accept space-separated values; relationships use
page IDs. Inspect all flags with:

```bash
uv run python -m rag_service.commands.documentation.create_doc_page --help
```

### Write and connect the page

1. Add the required `subtitle` and the selected template's body.
2. Add type-specific metadata, such as `dataset_version` for evaluation results
   or `tags` for release notes.
3. Verify behavior and examples against authoritative sources. Keep evaluation
   findings tied to the specific dataset, configuration, and recorded run.
4. Add ordinary pages to `fern/docs.yml`. Changelog entries use the existing
   changelog tab instead of individual navigation entries.
5. Add useful links and page relationships. Keep page IDs stable.
6. Generate dates, preview, and validate using the procedures in this guide.

Fern supplies the H1; start MDX bodies at H2. Use published site paths for
inter-page links and snippets for content that needs a shared source.

## Update an existing page

Edit the authored source and verify changed claims. Keep its ID stable. If a
filename, URL, or navigation location changes, update navigation and incoming
links. If an ID changes, update metadata references and regenerate the registry.

Reassess the description, subtitle, metadata, and related reading when scope
changes. Use the writing guides and applicable template; the new-page authoring
skill is not an existing-page editing workflow.

Regenerate dates after substantive edits:

```bash
uv run python -m rag_service.commands.documentation.update_last_modified
```

New authored pages and pages with substantive uncommitted changes use today's
date; otherwise the date comes from the latest substantive Git change. Changes
only to `last_modified` are ignored. The glossary has its own generator-owned
date. Review all generated diffs and rerun date generation if edits or the
relevant date change before publication.

## Add a changelog entry

Use `fern/docs/pages/changelog/YYYY-MM-DD.mdx` and the release-note template.
Inspect an existing entry for that date before deciding whether to extend it.
Preserve existing content and IDs; do not combine unrelated releases merely
because their dates match.

Explain user impact under **What's changed**, include applicable breaking
changes, migration steps, or known issues, and finish with **Related
documentation**. Add required `tags`; include an application version only when
verified. The release date in the filename and generated `last_modified` date
serve different purposes.

For a new entry, initialize it with `create_doc_page`, then add the subtitle,
tags, and template body. Fern already reads the directory through its changelog
tab. Generate dates and validate as for other authored pages.

## Update terminology and the glossary

Use [terminology.md](terminology.md) for naming decisions and distinctions.
Use [glossary.yml](../docs/data/glossary.yml) for reader-facing definitions.
Resolve conflicting terminology before applying an affected definition.

Check where readers encounter a candidate term in `fern/docs/pages/`, as well as
other relevant documentation. Compare existing names, aliases, and concepts to
avoid duplicates. Verify project-specific meaning against implementation where
needed. Define useful concepts rather than every technical word or code symbol.

Edit the YAML source, then regenerate both the glossary and Vale vocabulary:

```bash
uv run python scripts/generate_glossary.py
```

The generator validates entries and relationships, renders
`fern/docs/pages/reference/glossary.mdx`, and builds
`styles/config/vocabularies/RAGService/accept.txt`. Its date is based on changes
to parsed term data; comments and top-level metadata do not advance the date.

For a spelling allowance without a glossary definition, edit
[manual-accept.txt](../styles/config/vocabularies/RAGService/manual-accept.txt)
and run the same generator. Vocabulary allowances do not override separate
terminology rules. Edit prose rules under `styles/RAGService/` and their
activation in `.vale.ini` when an authorized rule change is needed.

## Regenerate derived files

Edit the source of a generated file, then run its generator. Review source and
output changes together; do not patch generated outputs by hand.

| Output | Source or trigger | Command |
| --- | --- | --- |
| `page-registry.yml` | Add/remove pages; change IDs, content types, or archive status | `uv run python -m rag_service.commands.documentation.update_page_registry` |
| Authored-page `last_modified` | Substantive MDX edits and Git history | `uv run python -m rag_service.commands.documentation.update_last_modified` |
| Glossary and Vale vocabulary | `docs/data/glossary.yml` and `styles/config/vocabularies/RAGService/manual-accept.txt` | `uv run python scripts/generate_glossary.py` |
| `fern/openapi.yml` | FastAPI app, routes, models, and their descriptions | `uv run python -m rag_service.commands.generate_openapi` |

All four commands support `--check`. The registry records active MDX page IDs
and content types plus generated API page IDs; it does not control navigation.
Page initialization already regenerates it. OpenAPI changes may also require
updates to prose guides and request/response examples.

## Preview the site

For the authored site directly:

```bash
fern docs dev
```

For shared flowchart colors, use the Mermaid wrapper instead:

```bash
python3 doc-infrastructure/scripts/fern_mermaid.py dev
```

The wrapper copies `fern/` into `.generated/fern/`, injects palette definitions
into `flowchart` and `graph` blocks, and refreshes the copy as sources or the
palette change. It preserves authored sources and leaves other diagram types
unchanged. Stop the preview with Ctrl+C.

Assign semantic classes such as `core`, `artifact`, or `external` to diagram
nodes. Keep colors in the palette; see the style guide's diagram conventions
and [Mermaid guide](diagram-styles/README.md) for commands and limitations.

Review navigation, links, tables, components, code examples, and diagrams in
light and dark modes. For a styled copy without starting a server:

```bash
python3 doc-infrastructure/scripts/fern_mermaid.py prepare
python3 doc-infrastructure/scripts/fern_mermaid.py check
```

These commands write the ignored `.generated/fern/` directory. The wrapper's
`preview` creates a hosted preview and `publish` publishes documentation; they
are external actions, not local validation. Current CI publishes `fern/`
directly and does not invoke the Mermaid wrapper.

## Validate changes

Run the complete check from the repository root:

```bash
uv run python -m rag_service.commands.documentation.validate_docs
```

It checks the registry, frontmatter, content-type structure, Fern authoring
rules, MDX lint, generated dates, glossary outputs, Vale, OpenAPI freshness,
and Fern configuration. It stops at a failing stage.

Before merging into `main` or publishing, run:

```bash
uv run python -m rag_service.commands.documentation.validate_docs --production
```

Regular validation permits draft and review pages. Production requires every
MDX page under `fern/docs/pages/` to be `published` or `deprecated`, even when
omitted from navigation. It rejects archived pages and a Fern `draft` value
unless absent or explicitly `false`. Finalize unfinished pages or move them
outside that directory and remove their navigation and incoming references.

### Focused checks and coverage limits

| Check | Command |
| --- | --- |
| MDX page and template formatting | `npm run lint:docs` |
| Registry freshness | `uv run python -m rag_service.commands.documentation.update_page_registry --check` |
| Authored dates | `uv run python -m rag_service.commands.documentation.update_last_modified --check` |
| Glossary and vocabulary freshness | `uv run python scripts/generate_glossary.py --check` |
| OpenAPI freshness | `uv run python -m rag_service.commands.generate_openapi --check` |
| Prose on one help page | `vale fern/docs/pages/get-started/quickstart.mdx` |
| Source Fern configuration and API definition | `fern check` |

`lint:docs` collects only `.mdx` files in `fern/docs/pages/` and
`doc-infrastructure/templates/`, including the template fixtures. It does not
lint Markdown READMEs, guides, prompts, or skill files. The full validator's
Vale pass targets `fern/docs/pages/`; it is not a review of every repository
document. Review changed Markdown separately, including its links and commands.
Passing validation also does not prove technical accuracy or deployed behavior.

### Resolve failures

| Failure | Action |
| --- | --- |
| Invalid metadata or page relationship | Check the content model and registry; correct source IDs and regenerate when necessary. |
| Stale generated output | Run its generator and inspect the diff. |
| Missing or misplaced sections | Compare the page with its content-type template. |
| Vale error | Follow the named rule; make source or authorized rule changes rather than editing generated prose. |
| Fern configuration or link failure | Check navigation, published URLs, snippet paths, and API definitions. |
| Production lifecycle failure | Finalize the page or remove unfinished content from the published page tree. |
| Missing command or dependency | Complete the tool setup before rerunning validation. |

## Publish and verify

[GitHub Actions CI](../.github/workflows/ci.yml) publishes on pushes to `main`
and manual CI runs on `main`, after the test, WordPress MySQL rate-limit, and
dependency-audit jobs succeed. The test job uses production documentation
validation on `main` and regular validation on other refs.

1. Review source and generated changes, preview the site, and pass production
   validation.
2. Follow the repository's approval process to commit and integrate changes
   into `main`, then push when authorized.
3. Check the CI run for that commit and **Publish Fern documentation**.
4. Review the [published site](https://python-rag-service.docs.buildwithfern.com/)
   and the subsequent **Check published documentation links** job.

Publication skips a validated commit when remote `main` already has a newer
commit. Code-only changes can also trigger publication. To republish without a
new commit, run **Actions > CI > Run workflow** on `main`; the same checks apply.

CI needs the repository secret `FERN_TOKEN` for the organization configured in
`fern/fern.config.json`. The
[documentation link check](../.github/workflows/docs-link-check.yml) also runs
weekly on Monday and can be started manually. A link-check failure occurs after
publication and does not roll it back.
