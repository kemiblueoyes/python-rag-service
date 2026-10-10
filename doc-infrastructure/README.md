# Maintain the documentation

Use this guide to create, update, validate, and publish the Python RAG Service documentation.

Run every command from the repository root. This README belongs in `doc-infrastructure/`; its file links are relative to that directory.

## Where to make changes

| Location | What it owns |
| --- | --- |
| [`fern/docs/pages/`](../fern/docs/pages/) | Authored MDX pages, release notes, and the generated glossary |
| [`fern/docs.yml`](../fern/docs.yml) | Site navigation, URL structure, branding, and publishing instance |
| [`fern/docs/snippets/`](../fern/docs/snippets/) | Content reused across pages |
| [`templates/`](templates/) | Expected structure for each content type |
| [`prompts/`](prompts/) | Optional AI prompts for authoring pages and reviewing style, plus starter input lists |
| [`content-model.yml`](content-model.yml) | Required metadata and allowed values |
| [`style-guide.md`](style-guide.md), [`terminology.md`](terminology.md), and [`fern-platform-rules.md`](fern-platform-rules.md) | Writing, terminology, and Fern authoring conventions |
| [`docs/data/glossary.yml`](../docs/data/glossary.yml) | Glossary definitions and aliases |
| [`styles/`](../styles/) and [`.vale.ini`](../.vale.ini) | Vale prose rules and configuration |
| [Documentation commands](../src/rag_service/commands/documentation/) | Page creation, metadata updates, and validation |

## Set up the tools

Use a Git checkout with its history available; date generation reads Git history.

Install Python 3.12, uv, Node.js 22, and npm. Then install the locked project dependencies:

```bash
uv sync --dev --locked
npm ci
```

Install the Fern CLI version recorded in `fern/fern.config.json`:

```bash
FERN_VERSION=$(node -p "require('./fern/fern.config.json').version")
npm install -g "fern-api@${FERN_VERSION}"
```

Install Vale to match the version in the [CI workflow](../.github/workflows/ci.yml), currently `3.22.0`. The repository already includes the Microsoft and project style files. Check that the CLI is available:

```bash
vale --version
```

For installation options, see the [Vale releases](https://github.com/vale-cli/vale/releases/tag/v3.22.0).

Local preview also requires pnpm on your `PATH`. See [Fern's preview prerequisites](https://buildwithfern.com/learn/docs/preview-publish/preview-changes) for setup.

## Create a page

### 1. Choose the goal and template

Check the documentation IA before adding a page. Define its user goal, stable page ID, content type, audience, and relationships to existing pages.

Read the [style guide](style-guide.md), [terminology](terminology.md), [Fern rules](fern-platform-rules.md), and appropriate template:

| Content type | Template |
| --- | --- |
| `overview` | [Overview](templates/overview.mdx) |
| `how_to` | [How-to](templates/how-to.mdx) |
| `tutorial` | [Tutorial](templates/tutorial.mdx) |
| `explanation` | [Explanation](templates/explanation.mdx) |
| `general_reference` | [General reference](templates/general-reference.mdx) |
| `eval_results` | [Evaluation results](templates/evaluation-results.mdx) |
| `release_note` | [Release note](templates/release-note.mdx) |

API endpoint reference pages are generated from OpenAPI. Use the API update procedure below for those pages.

### 2. Create the draft metadata

Adapt this example to the planned page:

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

The command creates a new file with `lifecycle_status: draft` and updates `page-registry.yml`. It rejects an existing file, a reused page ID, an unknown controlled value, or a path outside `fern/docs/pages/`. Filenames must use lowercase kebab-case and end in `.mdx`.

It creates frontmatter only. It does **not** insert the selected template's body or a `subtitle`.

Optional flags add `--components`, `--prerequisites`, `--next-steps`, and `--related-pages`. List flags take space-separated values. Page relationships use page IDs from the registry.

For all flags:

```bash
uv run python -m rag_service.commands.documentation.create_doc_page --help
```

### 3. Write and connect the page

1. Add the required `subtitle` and write the body using the selected template.
2. Add type-specific metadata: `dataset_version` for evaluation results or `tags` for release notes.
3. Check descriptions, commands, configuration, and examples against the implementation.
4. Add an ordinary page to the appropriate section of `fern/docs.yml`. Release notes belong in `fern/docs/pages/changelog/`, which Fern reads through the changelog tab.
5. Add or update relevant links and metadata relationships on other pages.
6. Generate `last_modified` and validate using the procedures below.

Fern creates the page's H1 from its title; start the MDX body at H2. Use published site paths for links between MDX pages. Use snippets when multiple pages need identical content.

Regular validation allows draft and review pages. Before merging into `main`, finish the page and set its status to `published`, or move unfinished work outside `fern/docs/pages/` and remove its navigation entries and incoming links. Production validation checks every page in that directory, even pages omitted from navigation.

## Update an existing page

Edit the MDX source and check the relevant product code or configuration before changing a behavior claim. Keep its page ID stable so metadata relationships continue to resolve.

If you change a filename, navigation location, or URL, update `fern/docs.yml` and affected links. If you change a page ID, update references to that ID as well.

After editing, regenerate date metadata:

```bash
uv run python -m rag_service.commands.documentation.update_last_modified
```

This updates authored pages under `fern/docs/pages/`. New pages and pages with substantive uncommitted changes use today's date. Otherwise, the date comes from the latest substantive Git change. Changes only to `last_modified` are ignored.

The glossary generator owns the glossary page's date. Rerun date generation if you make further edits or commit on a later date.

## Optional AI authoring and review prompts

The [prompts directory](prompts/) contains basic helpers for working with an AI assistant. Use them when useful; they are optional.

| File | When to use it |
| --- | --- |
| [`author-doc-page.md`](prompts/author-doc-page.md) | Create or substantially update a page using its template, project writing guidance, planned metadata, and relevant product sources. |
| [`review-doc-style.md`](prompts/review-doc-style.md) | Request an advisory review of issues that need editorial judgment, such as clarity, audience fit, technical depth, unsupported guarantees, and duplication. |
| [`copy-paste-inputs.md`](prompts/copy-paste-inputs.md) | Start an authoring or review request with reusable input lists. Adapt them to the page and the selected prompt. |

Give the assistant the selected prompt, page or draft, content-type template, page goal, and relevant product sources. For authoring, also provide the planned metadata listed in the prompt.

The style-review prompt complements Vale and the documentation validators by focusing on editorial judgment. Review the assistant's suggestions against the project guidance and implementation, then run the validation commands below.

## Update generated files

Edit each source, then run its generator. Include changed generated files in the same commit as their source changes.

### Page registry

After adding or removing pages, changing page IDs or content types, or archiving pages:

```bash
uv run python -m rag_service.commands.documentation.update_page_registry
```

The registry records page IDs and content types from active MDX pages, plus the generated API page IDs defined in the command. It does not control navigation. The page-creation command already updates it.

### Glossary and Vale vocabulary

Edit `docs/data/glossary.yml` for definitions and aliases.

To allow a word in Vale without adding a glossary definition, edit `styles/config/vocabularies/RAGService/manual-accept.txt`.

After either change:

```bash
uv run python scripts/generate_glossary.py
```

This generates:

- `fern/docs/pages/reference/glossary.mdx`
- `styles/config/vocabularies/RAGService/accept.txt`

Edit project prose rules in `styles/RAGService/`. Enable or disable individual rules in `.vale.ini`. Vocabulary entries allow spellings; they do not override separate terminology or substitution rules.

### API reference

Update request models, response models, route descriptions, and examples in the FastAPI source, then regenerate the specification:

```bash
uv run python -m rag_service.commands.generate_openapi
```

This writes `fern/openapi.yml`, which Fern uses to generate endpoint reference pages. Update related guides and error documentation when the API behavior changes.

## Preview and validate

Start the local preview:

```bash
fern docs dev
```

Open the URL printed in the terminal. Review navigation, layout, tables, components, code examples, and links.

Run the complete validation command:

```bash
uv run python -m rag_service.commands.documentation.validate_docs
```

It checks the page registry, required metadata, content-type structure, Fern authoring rules, Markdown lint, generated dates, glossary outputs, Vale, OpenAPI, and Fern configuration. It stops at a failing stage; fix that stage and rerun.

Before merging or publishing:

```bash
uv run python -m rag_service.commands.documentation.validate_docs --production
```

Production validation requires every MDX page under `fern/docs/pages/` to use `lifecycle_status: published` or `deprecated`. It rejects draft, review, and archived pages, and a Fern `draft` field unless absent or explicitly `false`.

For focused checks while editing:

| Check | Command |
| --- | --- |
| Markdown and MDX formatting | `npm run lint:docs` |
| Page registry freshness | `uv run python -m rag_service.commands.documentation.update_page_registry --check` |
| Date metadata freshness | `uv run python -m rag_service.commands.documentation.update_last_modified --check` |
| Glossary and vocabulary freshness | `uv run python scripts/generate_glossary.py --check` |
| OpenAPI freshness | `uv run python -m rag_service.commands.generate_openapi --check` |
| Prose on one page | `vale fern/docs/pages/get-started/quickstart.mdx` |
| Fern configuration and API definition | `fern check` |

Use the full command before merging. A passing check does not establish that a product description is correct; verify changed behavior and runnable examples against the service.

## Fix common validation failures

| Failure | Action |
| --- | --- |
| Missing or invalid metadata | Add required fields and use allowed values from `content-model.yml`. Check type-specific requirements. |
| Unknown page relationship or duplicate ID | Correct the source page IDs or relationships, then regenerate the registry. |
| Stale generated output | Run the corresponding generator above and review its diff. |
| Content-type structure failure | Compare the page with its template and the validator's required sections. |
| Vale finding | Follow the named rule's message. For an intentional exception, change the relevant vocabulary or rule configuration. |
| Fern configuration or link failure | Check navigation paths, published URLs, snippet paths, and the API definition. |
| Production lifecycle failure | Publish completed content or move unfinished and archived files outside `fern/docs/pages/`; update navigation and links. |
| Missing CLI or dependency | Complete the tool setup above. |

## Publish and verify

Publishing is handled by [GitHub Actions CI](../.github/workflows/ci.yml).

1. Review the source and generated-file changes, preview the pages, and pass production validation.
2. Commit and merge the changes into `main`.
3. Open **Actions > CI** and check the run for that commit.
4. Confirm that the test job, WordPress MySQL rate-limit job, and dependency audit succeed. The test job includes production documentation validation.
5. Confirm that **Publish Fern documentation** succeeds, then review the changed pages on the [published site](https://python-rag-service.docs.buildwithfern.com/).
6. Check **Check published documentation links** for broken links.

Other branches and pull requests run checks without publishing. A successful code-only change on `main` also triggers publication. Publication skips a commit if `main` already has a newer one.

To republish without a new commit, open **Actions > CI > Run workflow** and select `main`. The same checks run before publication.

The publish job needs the repository secret `FERN_TOKEN` for the `doc-landscape` organization. If it is missing, create a Fern token with `fern token` and store it under **Settings > Secrets and variables > Actions**.

The [Documentation link check workflow](../.github/workflows/docs-link-check.yml) also runs every Monday and can be started manually. A link-check failure occurs after publication and does not roll it back; fix the reported links and push the correction.

