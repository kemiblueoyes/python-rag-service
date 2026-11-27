# Python RAG Service

A platform-agnostic Python service for indexing documentation, performing hybrid retrieval, and generating grounded answers with citations.

**[Documentation](https://python-rag-service.docs.buildwithfern.com/) · [Quickstart](https://python-rag-service.docs.buildwithfern.com/docs/get-started/quickstart) · [System architecture](https://python-rag-service.docs.buildwithfern.com/docs/architecture/system-architecture)**

The first implementation uses WordPress as both the content source and reference client. The core indexing, retrieval, and answer-generation layers remain independent of WordPress so developers can add other sources and clients.

## Project status

The core indexing, search, grounded-answer, WordPress integration, and evaluation workflows are implemented and tested. Developer documentation is published. A separate operations runner and n8n workflows support scheduled indexing, retrieval evaluation, quality checks, Jira regression reporting, and failure alerts.

See the [implementation roadmap](docs/design/004-implementation-roadmap.md) for the remaining work and planned extensions.

## Capabilities

- **Index documentation:** Retrieve WordPress content, map it to a platform-neutral document model, and split it into chunks that preserve heading context. Rebuild the index or update it incrementally.
- **Retrieve relevant content:** Combine vector search with BM25 keyword search, merge their rankings, and rerank candidates with Voyage AI.
- **Handle unsupported queries:** Apply a retrieval support gate that can return no results when candidate scores fall below the configured cutoff.
- **Generate grounded answers:** Assemble retrieved evidence within a token budget, generate answers through OpenAI, and validate citation identifiers against the supplied sources.
- **Expose search and answers through an API:** Authenticate requests with an API key and support metadata filters.
- **Integrate with WordPress:** Provide Search and Ask interfaces through a reference plugin with source links, clickable citations, and loading and error states.
- **Evaluate quality:** Measure retrieval, check answer structure and citation behavior, and review generated answers against versioned expectations.
- **Automate operations:** Run indexing and retrieval evaluation through a separate authenticated runner, with n8n workflows for scheduling, quality routing, Jira regressions, and failure alerts.

## Get started

Use the [quickstart](https://python-rag-service.docs.buildwithfern.com/docs/get-started/quickstart) to install the project, configure providers, index WordPress content, and send your first authenticated search request.

Search requires Python 3.12, [uv](https://docs.astral.sh/uv/), a Voyage AI API key, a reachable Qdrant instance, and a WordPress site with accessible REST content. Answer generation also requires an OpenAI API key.

| Task | Documentation |
| --- | --- |
| Install and configure the service | [Install](https://python-rag-service.docs.buildwithfern.com/docs/get-started/install) · [Configure the service](https://python-rag-service.docs.buildwithfern.com/docs/get-started/configure-the-service) |
| Build and update an index | [Index WordPress content](https://python-rag-service.docs.buildwithfern.com/docs/index-content/index-wordpress-content) |
| Search indexed content | [Search documentation](https://python-rag-service.docs.buildwithfern.com/docs/search-and-answer/search-documentation) |
| Generate answers from indexed content | [Generate grounded answers](https://python-rag-service.docs.buildwithfern.com/docs/search-and-answer/generate-grounded-answers) |
| Add the WordPress client | [Integrate with WordPress](https://python-rag-service.docs.buildwithfern.com/docs/integrate/integrate-with-wordpress) |
| Evaluate retrieval and answers | [Run the evaluation](https://python-rag-service.docs.buildwithfern.com/docs/evaluate/run-the-evaluation) |
| Automate indexing and retrieval evaluation | [Operations overview](https://python-rag-service.docs.buildwithfern.com/docs/operations/overview) · [Run the operations runner](https://python-rag-service.docs.buildwithfern.com/docs/operations/run-operations-runner) · [Set up the n8n workflow](https://python-rag-service.docs.buildwithfern.com/docs/operations/set-up-n8n-workflow) · [How the n8n workflow works](https://python-rag-service.docs.buildwithfern.com/docs/operations/how-n8n-workflow-works) |

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/search` | Return ranked documentation chunks without generating an answer. |
| `POST /v1/answer` | Retrieve documentation and generate an answer with source references. |
| `GET /health` | Check whether the API is running. |

Search and answer require an `X-API-Key` header. Both use the same retrieval pipeline. Indexing runs through CLI commands or the separate operations runner rather than a public search/answer endpoint.

See the [API reference](https://python-rag-service.docs.buildwithfern.com/reference/search) for request schemas, filters, responses, and errors. A running local service also exposes interactive API documentation at `http://127.0.0.1:8000/docs`.

## Architecture

The indexing pipeline retrieves content through a connector, normalizes it into canonical documents, creates heading-aware chunks, generates Voyage embeddings, and maintains a Qdrant index. Retrieval combines Qdrant vector results with local BM25 keyword results before reranking and support gating.

The answer workflow selects retrieved chunks within a context budget, constructs a grounded prompt, requests a structured answer, and checks evidence-sufficiency and citation consistency. Citation validation checks source identifiers; whether a source supports a claim is assessed separately during qualitative evaluation.

The WordPress connector imports content. The WordPress client consumes the API through a server-side proxy that keeps the service API key out of browser JavaScript. These components remain separate from the core RAG logic.

Read the [system architecture](https://python-rag-service.docs.buildwithfern.com/docs/architecture/system-architecture) and [architecture decision records](docs/design/adr/) for the component boundaries and design choices.

## Operations and automation

The operations runner in [`src/rag_service/operations/`](src/rag_service/operations/) runs separately from the public API and uses its own authentication key. It accepts indexing and retrieval-evaluation jobs, tracks their status, and preserves job results for polling and recovery.

The included n8n workflows schedule WordPress indexing, evaluate retrieval when content changes, compare results with quality policies, report regressions in Jira, and send failure alerts. Configure the runner connection, credentials, and policy files in your n8n environment. After indexing publishes updated chunks, the public API refreshes its in-memory BM25 index on the next search or answer request.

See the [operations runner guide](https://python-rag-service.docs.buildwithfern.com/docs/operations/run-operations-runner) for setup, manual verification, Docker connectivity, and recovery behavior. [Set up the n8n workflow](https://python-rag-service.docs.buildwithfern.com/docs/operations/set-up-n8n-workflow) and [How the n8n workflow works](https://python-rag-service.docs.buildwithfern.com/docs/operations/how-n8n-workflow-works) cover scheduling, quality routing, Jira reporting, and alerts. Workflow exports are in [`automation/n8n/`](automation/n8n/). The [retrieval quality policy](automation/n8n/policies/README.md) records the approved baseline and how to mount the policy files for n8n.

## Evaluation

The evaluation framework measures retrieval and answer quality separately using a versioned dataset, automated checks, and human review.

The recorded Doc Landscape baseline uses dataset version `1.5` with 22 cases. Retrieval passed 21 of 22 cases and returned no chunks for all 8 expected-empty queries. A separately recorded answer run passed all 22 structural checks, and human review passed all 14 answerable responses.

These results describe saved runs on one corpus. The known retrieval limitation is incomplete source coverage for a compound query. Changes to content, models, prompts, or retrieval settings can change the results.

See [recorded evaluation results](https://python-rag-service.docs.buildwithfern.com/docs/evaluate/recorded-evaluation-results) for the run dates, metrics, limitations, and links to the saved reports. The [retrieval failure analysis](docs/evaluation/retrieval-failure-analysis.md) documents the experiments that led to the current pipeline.

## Documentation engineering

The documentation is maintained as part of the repository, with an explicit content model and automated checks.

- **Structured authoring:** Defined content types, required metadata, page templates, and a generated page registry.
- **Authoring tools:** Commands to create pages, update metadata, and generate the glossary.
- **Quality checks:** Validation for page structure, frontmatter, Fern rules, links, OpenAPI, and project terminology. Vale checks prose against Microsoft and project-specific style rules.
- **Publishing:** GitHub Actions validates documentation and runs service tests, WordPress tests, and dependency audits before publishing from `main`. A separate workflow checks published links.

Start with the [documentation maintainer guide](doc-infrastructure/README.md) for page creation, glossary generation, preview, and validation. Standards in [`doc-infrastructure/`](doc-infrastructure/) include the content model, templates, style guide, terminology, technical-accuracy rules, Fern platform rules, and the Mermaid palette. Authoring and validation commands live in [`src/rag_service/commands/documentation/`](src/rag_service/commands/documentation/).

Agent workflows for new pages, drift audits, glossary updates, and changelog entries are in [`.agents/skills/`](.agents/skills/). The maintainer guide explains when to use each skill. Prompts in `doc-infrastructure/prompts/` cover narrower tasks and are transitional. The [CI workflow](.github/workflows/ci.yml) records the checks used for publication.

## Development

After installing development dependencies, run these checks from the repository root:

```bash
uv run pytest
uv run ruff check .
uv run mypy
```

Validate documentation with:

```bash
uv run python -m rag_service.commands.documentation.validate_docs
```

Documentation validation also requires the npm dependencies, Fern CLI, and Vale. Use `--production` to check publication status before publishing. The [CI workflow](.github/workflows/ci.yml) records the tool setup and checks used for publication.

Audit the locked Python and npm dependencies with:

```bash
bash scripts/audit-locked-dependencies.sh
```

## Repository guide

| Path | Contents |
| --- | --- |
| [`src/rag_service/`](src/rag_service/) | Connectors, indexing, retrieval, generation, API, operations runner, and command implementations |
| [`src/rag_service/operations/`](src/rag_service/operations/) | Authenticated runner for indexing and retrieval-evaluation jobs |
| [`clients/wordpress/`](clients/wordpress/) | WordPress reference client and its tests |
| [`tests/`](tests/) | Python service and documentation-tool tests |
| [`automation/n8n/`](automation/n8n/) | Indexing, retrieval-quality, Jira regression, and failure-alert workflows. [`policies/README.md`](automation/n8n/policies/README.md) explains the quality policy and approved baseline |
| [`evaluation/`](evaluation/) | Evaluation datasets and recorded report snapshots |
| [`fern/`](fern/) | Published documentation source and Fern configuration |
| [`doc-infrastructure/`](doc-infrastructure/) | [Maintainer guide](doc-infrastructure/README.md), content model, templates, style, terminology, technical-accuracy and Fern platform rules, Mermaid palette, and page registry |
| [`docs/design/`](docs/design/) | Project design, implementation roadmap, and architecture decisions |
| [`docs/evaluation/`](docs/evaluation/) | Retrieval experiments, failure analysis, and evaluation findings |
| [`.agents/skills/`](.agents/skills/) | Agent skills for authoring pages, auditing docs against code, updating the glossary, and adding changelog entries. The maintainer guide explains when to use each skill |

## License

This project is licensed under the [MIT License](LICENSE).
