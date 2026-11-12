# Repository guidance

Python RAG Service indexes documentation, retrieves evidence, and generates answers with citations. The Python service lives in `src/rag_service/`; the reference WordPress client lives in `clients/wordpress/`.

All paths below are relative to the repository root. Run commands from that root.

## Documentation map

Use this map to start discovery, then search for additional docs and examples related to the task. Verify these paths and their claims against the current tree. This map is not an exhaustive inventory or evidence that the docs are current.

| Documentation surface | Location | Implementation or evidence to compare |
| --- | --- | --- |
| Project overview and developer setup | `README.md` | `pyproject.toml`, `package.json`, `.github/workflows/ci.yml` |
| Published guides, tutorials, reference prose, and release notes | `fern/docs/pages/` | Relevant modules in `src/rag_service/`, commands, and tests |
| Site navigation | `fern/docs.yml` | Page sources and navigation targets |
| Shared content | `fern/docs/snippets/` | Pages that include each snippet and the implementation its claims describe |
| Public API contract and examples | `fern/openapi.yml`, `fern/docs/pages/api/` | `src/rag_service/api/` routes, models, authentication, and errors; `tests/api/` |
| Configuration and setup examples | `.env.example`, `fern/docs/pages/get-started/`, `fern/docs/pages/reference/configuration-reference.mdx` | `src/rag_service/config.py`, provider factories, and settings consumers |
| CLI usage and command examples | Examples throughout the guides; Command-line help text defined in `src/rag_service/commands/` | Command implementations and their tests; inspect side effects before running commands |
| Operations and automation | `docs/operations/README.md`, `automation/n8n/policies/README.md` | `src/rag_service/operations/`, workflow exports and policies in `automation/n8n/` |
| WordPress integration | `fern/docs/pages/integrate/` | `clients/wordpress/` implementation and tests; `src/rag_service/connectors/wordpress/` for content ingestion |
| Architecture, decisions, and roadmap | `docs/design/`, `docs/design/adr/`, `fern/docs/pages/architecture/` | Current implementation and tests; distinguish planned behavior from implemented behavior |
| Evaluation methods and results | `fern/docs/pages/evaluate/`, `docs/evaluation/`, `evaluation/datasets/CHANGELOG.md`, `evaluation/reports/` | `src/rag_service/evaluation/`, evaluation commands, datasets, and saved reports |
| Documentation maintenance and standards | `doc-infrastructure/README.md`, `doc-infrastructure/` | `src/rag_service/commands/documentation/`, `scripts/`, `styles/`, `.vale.ini` |

Recorded evaluation reports describe particular runs. Do not present their results
as guarantees about the current corpus or configuration.

## Documentation changes

- Read `doc-infrastructure/README.md` before authoring or restructuring published docs. It describes setup, page creation, metadata, generation, and validation.
- Follow `doc-infrastructure/content-model.yml`, the applicable template in
  `doc-infrastructure/templates/`, and the style, terminology, and Fern platform guides in that directory.
- Fern creates the page H1: start MDX bodies at H2. Use published site paths for
  inter-page MDX links. Keep page IDs stable and update navigation and affected
  links when moving a page.
- Check behavior claims against the implementation. For an audit-only request, report mismatches without changing  docs or regenerating outputs. Cite both the documentation and the implementation evidence, and state coverage limits.

## Generated files

Edit the source and regenerate outputs when making changes; do not patch generated
outputs directly. The following commands write files. For an audit, use their
`--check` variants instead, with dependencies already available.

| Output | Source | Regenerate command |
| --- | --- | --- |
| `fern/openapi.yml` | FastAPI app, routes, and models in `src/rag_service/api/` | `uv run python -m rag_service.commands.generate_openapi` |
| `doc-infrastructure/page-registry.yml` | Active MDX page metadata and API page IDs in the registry command | `uv run python -m rag_service.commands.documentation.update_page_registry` |
| `fern/docs/pages/reference/glossary.mdx`, `styles/config/vocabularies/RAGService/accept.txt` | `docs/data/glossary.yml`, `styles/config/vocabularies/RAGService/manual-accept.txt` | `uv run python scripts/generate_glossary.py` |

For authored page date metadata, use
`uv run python -m rag_service.commands.documentation.update_last_modified`.
The glossary generator owns the glossary page's date.

## Validation

Choose checks relevant to the change and report what ran, what failed, and what could not be checked. Tool installation is documented in `doc-infrastructure/README.md`; CI setup is in `.github/workflows/ci.yml`.

| Change | Check |
| --- | --- |
| Published MDX pages and MDX templates | `npm run lint:docs` |
| Published docs, metadata, or generated documentation | `uv run python -m rag_service.commands.documentation.validate_docs` |
| Publication readiness | Same documentation validation command with `--production` |
| Python behavior | `uv run pytest` (or relevant tests for a focused change) |
| Python lint and types | `uv run ruff check .` and `uv run mypy` |
| WordPress client JavaScript | `npm run test:wordpress-client` |

Documentation validation requires Python and npm dependencies, Fern CLI, and Vale. `npm test` is a placeholder that exits with failure; use the named checks above.

## Keeping this guidance useful

If your changes move documentation, change how files are generated, or change validation commands, update the relevant guidance in this file. Whenever you change this file, tell the person you are working with what changed and why in your final response or handoff summary.

Keep detailed procedures in their existing guides and reusable audit procedures in
skills. Keep this file focused on durable repository guidance.
