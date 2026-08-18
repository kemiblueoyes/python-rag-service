# Python RAG Service

A platform-agnostic Python service for indexing documentation, performing semantic search, and generating grounded answers with citations.

The first implementation uses WordPress as both:

* the initial content source
* the initial client application

The core retrieval and answer-generation logic remains independent of WordPress so that additional content sources and clients can be added later.

## Project status

Active development. The indexing, semantic-search, and grounded-answer-generation paths are implemented and tested. The service can retrieve WordPress documents, normalize and chunk them, generate Voyage embeddings, maintain a Qdrant vector index, retrieve ranked chunks, and generate structured answers through OpenAI using only the selected evidence.

`POST /v1/search` and `POST /v1/answer` are implemented, tested, and represented in the generated OpenAPI specification. The answer endpoint reuses the shared retrieval pipeline and exposes grounded generation with token-budgeted context assembly, evidence-sufficiency detection, citation-integrity validation, and trusted source references.

See the implementation roadmap in `docs/design/007-implementation-roadmap.md`.

## Current capabilities

* WordPress REST API connector with configurable site profiles
* Platform-neutral canonical document model
* HTML cleanup and heading-aware chunking
* Stable document and chunk identifiers
* Voyage AI document and query embeddings
* Qdrant vector and chunk-metadata storage
* Full vector-index rebuilds
* Incremental handling of new, updated, unchanged, and removed documents
* Query validation and supported metadata filtering
* Similarity ranking with duplicate removal
* Configurable minimum retrieval score for weak-result filtering
* Retrieval-service factory for application-wide dependency wiring
* Public `POST /v1/search` endpoint
* Public `POST /v1/answer` endpoint
* Shared retrieval service used by both public endpoints
* Explicit search and answer request/response schemas
* Insufficient-evidence responses for unsupported questions
* Standard API error responses for validation, retrieval, and answer-generation failures
* FastAPI-generated OpenAPI and interactive API documentation for both endpoints
* API tests for successful, empty-result, validation-error, service-unavailable, and OpenAPI behavior
* Live embedding, storage, search, and filtering smoke test
* Live retrieval-service smoke tests against indexed WordPress content
* Live end-to-end verification through both public API workflows
* Configurable context-token budget with complete chunks preserved in retrieval order
* Request-local source identifiers such as `S1`, `S2`, and `S3`
* Provider-neutral prompt, token-counter, and language-model interfaces
* OpenAI Responses API integration with structured Pydantic output
* Grounded-answer prompt that treats retrieved content as evidence rather than instructions
* Grounded answer responses with validated source references
* Evidence-sufficiency detection with consistent citation requirements
* Citation-integrity validation for inline and structured citation identifiers
* Answer-generation factory for application-wide dependency wiring
* Live end-to-end answer-generation smoke test with a reviewable Markdown report

## Public API

The service is intentionally designed around two public endpoints:

| Endpoint | Status | Purpose |
|---|---|---|
| `POST /v1/search` | Implemented | Retrieve relevant documentation chunks without generating an answer. |
| `POST /v1/answer` | Implemented | Retrieve relevant documentation and generate a grounded answer with validated sources. |

Both endpoints use the same retrieval pipeline. `POST /v1/answer` builds on the retrieved results by running the grounded answer-generation and citation-validation workflow.

Content indexing runs through an internal command or administrative process rather than a public endpoint.

### `POST /v1/search`

The search endpoint accepts a natural-language query, optional metadata filters, and an optional result limit.

Example request:

```json
{
  "query": "How does metadata improve retrieval?",
  "filters": {
    "source": "wordpress",
    "content_type": "page"
  },
  "limit": 5
}
```

Supported filters are:

* `document_id`
* `source`
* `source_id`
* `content_type`

Each filter accepts either a single non-empty string or a list of non-empty strings.

Example successful response:

```json
{
  "query": "How does metadata improve retrieval?",
  "results": [
    {
      "chunk_id": "wordpress:page:1:chunk:0",
      "document_id": "wordpress:page:1",
      "title": "Metadata Strategy",
      "heading_path": ["Metadata filtering"],
      "excerpt": "Metadata can narrow the documents considered during retrieval.",
      "url": "https://example.com/metadata",
      "score": 0.91
    }
  ]
}
```

A valid query for which no result meets the configured retrieval threshold returns `200 OK` with an empty `results` array.

Invalid requests return `422 Unprocessable Content` using the standard error format:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": []
  }
}
```

If retrieval cannot complete because a required dependency such as the embedding provider or vector database is unavailable, the API returns `503 Service Unavailable`:

```json
{
  "error": {
    "code": "retrieval_unavailable",
    "message": "Search is temporarily unavailable.",
    "details": []
  }
}
```

Provider-specific exception details are not exposed through the public API.

See `docs/design/003-api-design.md` for the current API contract.

## Architecture

The system contains or will contain:

* a WordPress connector that retrieves and maps source content
* a canonical document model
* content normalization and heading-aware chunking
* embedding generation
* vector storage and semantic retrieval
* shared retrieval logic with validation, filtering, ranking, duplicate removal, and minimum-score filtering
* a public search API that maps HTTP requests to the shared retrieval service
* token-budgeted context assembly that preserves ranked source order
* grounded prompt construction
* a provider-neutral language-model interface with an OpenAI adapter
* structured answer parsing and evidence-sufficiency detection
* citation-integrity validation against the supplied context
* an answer generator that coordinates the complete generation workflow

The planned system also includes:

* `POST /v1/answer`
* a WordPress client for displaying search results and answers

The WordPress connector, retrieval pipeline, API layer, and  answer-generation layer remain separate so source-specific behavior does not spread through the RAG engine.

## Requirements

* Python 3.12
* [uv](https://docs.astral.sh/uv/)

## Local setup

Clone the repository and enter the project directory:

```bash
git clone https://github.com/kemiblueoyes/python-rag-service.git
cd python-rag-service
```

Install the project dependencies:

```bash
uv sync --dev
```

Create a local environment file:

```bash
cp .env.example .env
```

Add environment-specific URLs and credentials to `.env`. Never commit this
file or place real API keys in `.env.example`.

Run the application:

```bash
uv run uvicorn rag_service.api.app:app --reload
```

Open the health-check endpoint:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

FastAPI's generated API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

```text
http://127.0.0.1:8000/openapi.json
```

The interactive documentation can also be used to execute `POST /v1/search` against the configured retrieval service without using a terminal HTTP client.

## Indexing

### Provider configuration

The indexing pipeline uses
[Voyage AI](https://www.voyageai.com/) to create embeddings and
[Qdrant](https://qdrant.tech/) to store and search them. Before indexing,
create a Voyage API key and a Qdrant cluster with a database API key that has
manage/write access.

Configure the providers in `.env`:

```dotenv
EMBEDDING_PROVIDER=voyage
EMBEDDING_MODEL=voyage-4-lite
EMBEDDING_DIMENSION=1024
EMBEDDING_BATCH_SIZE=128
VOYAGE_API_KEY=your-voyage-api-key

VECTOR_DATABASE=qdrant
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=rag_chunks

RETRIEVAL_MIN_SCORE=0.50
```

`EMBEDDING_DIMENSION` must match the configured model's output. The default
`voyage-4-lite` configuration produces 1,024-number vectors. The Qdrant
adapter creates the collection and its required payload indexes when needed.

`RETRIEVAL_MIN_SCORE` sets the minimum similarity score a retrieved chunk must
meet before the retrieval service returns it. The current baseline is `0.50` and
can be adjusted later as retrieval evaluation becomes more systematic.

### WordPress configuration

Set the WordPress site URL, REST collections, and connector profile in `.env`:

```dotenv
WORDPRESS_BASE_URL=https://example.com
WORDPRESS_COLLECTIONS=["posts","pages"]
WORDPRESS_PROFILE=default
```

`WORDPRESS_COLLECTIONS` is a JSON array of REST API collection endpoints. The
standard, platform-neutral configuration retrieves posts and pages. Add any
custom post types exposed by a site, for example:

```dotenv
WORDPRESS_COLLECTIONS=["posts","pages","glossary"]
```

The default profile makes no assumptions about a site's custom fields or the
meaning of its page hierarchy. It maps standard WordPress fields, extracts
supported Yoast schema metadata when available, and records immediate page
parent relationships.

### Initial vector-index build

Run a full rebuild the first time the Qdrant collection is populated:

```bash
uv run python -m rag_service.commands.index_wordpress --rebuild-vector-index
```

A rebuild retrieves current WordPress content, processes every eligible
document, generates new embeddings, and replaces the corresponding Qdrant
points. It also writes:

* canonical documents to `data/wordpress-documents.json`
* retrieval-ready chunks to `data/wordpress-chunks.json`

Run a full rebuild after changing the embedding model, embedding dimension,
chunking rules, or stored payload structure.

### Incremental indexing

For normal indexing after the initial build, run:

```bash
uv run python -m rag_service.commands.index_wordpress
```

Each run compares current documents with the snapshot from the last successful
run:

* New documents are processed, embedded, and stored.
* Updated documents have their old chunks removed before current chunks are
  stored.
* Unchanged documents are not sent to Voyage or rewritten in Qdrant.
* Removed or unpublished documents have all their chunks removed from Qdrant.

The local snapshot is updated only after vector synchronization succeeds. If
Voyage or Qdrant fails, the next run can detect and retry the same changes.

Only indexable content documents are chunked. WordPress accordions configured
by the active connector profile are passed to the generic processing pipeline
as preserved HTML components.

### Live embedding and storage smoke test

The smoke test verifies one complete path through Voyage and Qdrant:

```text
sample chunk → document embedding → Qdrant storage
related question → query embedding → Qdrant search and filtering
```

Use a dedicated collection so test data cannot mix with indexed documentation:

```dotenv
QDRANT_COLLECTION=rag_chunks_smoke_test
```

Then run:

```bash
uv run python -m rag_service.commands.smoke_embedding_storage
```

The command prints the retrieved title, text, similarity score, and filter
results. It intentionally leaves the test point in Qdrant for inspection. The
test collection can be deleted from Qdrant after inspection. Restore
`QDRANT_COLLECTION=rag_chunks` before running WordPress indexing.

## Retrieval service

The shared retrieval service is the internal search pipeline that will be reused by
both `POST /v1/search` and `POST /v1/answer`. `RetrievalService`:

* validates non-empty queries and retrieval limits
* validates supported metadata filters
* generates query embeddings with the configured embedding provider
* searches the configured vector store
* preserves vector-similarity ranking
* removes duplicate chunks by `chunk_id`
* removes results below `RETRIEVAL_MIN_SCORE`

The current supported retrieval filters are:

* `document_id`
* `source`
* `source_id`
* `content_type`

The retrieval service is created through a factory so API endpoints can reuse the
same configured pipeline without wiring the embedding provider, vector store, and
minimum score independently.

Requests with a blank query, a limit below 1, an unsupported filter,
or an invalid filter value are rejected before provider calls are made.

The default minimum similarity score is `0.50`. Override it in `.env` when
needed:

```dotenv
RETRIEVAL_MIN_SCORE=0.50
```

### Live retrieval-service smoke test


The retrieval smoke test runs a set of deliberately different queries against the
indexed WordPress collection, including in-domain and out-of-domain questions. It
verifies that results preserve similarity ranking and that weak results are removed
by the configured minimum score.

Make sure `QDRANT_COLLECTION` points to the indexed documentation collection, then
run:

```bash
uv run python -m rag_service.commands.smoke_retrieval_service
```

The command writes a reviewable Markdown report to:

```text
data/retrieval_smoke_results.md
```

The report includes each query, returned result count, similarity scores, titles,
heading paths, URLs, chunk IDs, and chunk text. Queries for which no result meets
the minimum score are recorded as zero-result passes.

## WordPress connector profiles

WordPress installations commonly add custom post types, REST metadata, ACF
fields, and site-specific meanings for parent and child pages. Those decisions
belong in a connector profile rather than the reusable WordPress client,
mapper, or connector.

Profiles are defined with `WordPressConnectorProfile` and can provide:

* metadata mappings from either `acf` or WordPress `meta`
* optional value-label mappings
* document enrichers for site-specific relationships or roles
* HTML block classes that the processing pipeline must preserve intact

For example, a profile can expose a multi-value ACF field as canonical
metadata while preserving its list shape:

```python
from rag_service.connectors.wordpress.connector import WordPressConnectorProfile
from rag_service.connectors.wordpress.mapper import WordPressMetadataMapping

AUDIENCE_LABELS = {
    "TW": "Technical Writer",
    "DL": "Documentation Leader",
}

example_profile = WordPressConnectorProfile(
    metadata_mappings=(
        WordPressMetadataMapping(
            source="acf",
            source_key="target_audience",
            target_key="audience",
            value_map=AUDIENCE_LABELS,
        ),
        WordPressMetadataMapping(
            source="acf",
            source_key="target_audience",
            target_key="audience_codes",
        ),
    ),
    preserved_block_classes=frozenset({"wp-block-accordion"}),
)
```

If WordPress returns `target_audience` as `["TW", "DL"]`, the first mapping
produces `["Technical Writer", "Documentation Leader"]`. The second mapping
retains `["TW", "DL"]`. Fields without a `value_map` retain their original
shape and may contain scalar, list, or structured values.

The included `doc_landscape` profile demonstrates a complete site profile. It
configures The Doc Landscape's ACF fields and interprets selected parent pages
as series landing pages. Select it with:

```dotenv
WORDPRESS_PROFILE=doc_landscape
```

To add another site profile:

1. Create a module under `src/rag_service/profiles/` that defines a
   `WordPressConnectorProfile`.
2. Add the profile to `WORDPRESS_PROFILES` in
   `src/rag_service/profiles/wordpress.py`.
3. Set `WORDPRESS_PROFILE` to the registered profile name.

Document enrichers receive all source records and mapped canonical documents.
They can add site-specific metadata or document roles after the connector has
added generic WordPress parent relationships. They should not be added to
`src/rag_service/connectors/wordpress/` unless the behavior is meaningful for
WordPress installations generally.

`preserved_block_classes` is also site-profile configuration. Use it for
components such as accordions or tabs that must remain a single HTML block
during parsing. The default profile preserves no special block classes.

## Answer generation

The internal answer-generation workflow accepts a question and ranked retrieval results, then:

1. Selects complete retrieved chunks within the configured context-token budget.
2. Assigns request-local citation identifiers in retrieval order.
3. Constructs a grounded prompt containing the question and selected evidence.
4. Requests a structured answer from the configured language model.
5. Validates evidence sufficiency and citation integrity.
6. Returns only the sources cited by the generated answer.

Configure answer generation in `.env`:

```dotenv
GENERATION_PROVIDER=openai
GENERATION_MODEL=gpt-5.6-terra
GENERATION_REASONING_EFFORT=low
GENERATION_CONTEXT_BUDGET_TOKENS=8000
GENERATION_MAX_OUTPUT_TOKENS=1000
OPENAI_API_KEY=your-openai-api-key
```

`GENERATION_CONTEXT_BUDGET_TOKENS` applies to the fully rendered evidence blocks. Sources are included whole and in retrieval order; chunks are not truncated to fit the budget.

Citation identifiers such as `S1` and `S2` are local to one answer-generation request. Validation ensures that inline citations match the structured citation list and refer only to sources supplied to the model.

### Live answer-generation smoke test

Make sure Voyage, Qdrant, and OpenAI credentials are configured and that `QDRANT_COLLECTION` points to the indexed documentation collection. Then run:

```bash
uv run python -m rag_service.commands.smoke_answer_generation
```

The command exercises the complete live workflow:

```text
question → query embedding → Qdrant retrieval → context assembly
→ OpenAI generation → evidence-sufficiency and citation validation
```

It writes a reviewable Markdown report to:

```text
data/answer_generation_smoke_result.md
```

The report contains the question, generated answer, evidence-sufficiency result, validated source references, retrieval scores, and complete cited source text. It supports manual grounding review; automated answer-quality evaluation is planned for Phase 10.

## Development checks

Run the tests:

```bash
uv run pytest
```

Run Ruff:

```bash
uv run ruff check .
```

Format the code:

```bash
uv run ruff format .
```

Run MyPy:

```bash
uv run mypy
```

## Project structure

```text
.
├── docs/
│   └── design/
├── src/
│   └── rag_service/
│       ├── api/
│       │   └── routes/
│       ├── commands/
│       ├── connectors/
│       │   └── wordpress/
│       ├── embeddings/
|       |── generation/
│       ├── indexing/
│       ├── models/
│       ├── processing/
│       ├── profiles/
│       ├── retrieval/
│       ├── vectorstores/
│       └── config.py
├── tests/
│   ├── api/
│   ├── commands/
│   ├── connectors/
│   ├── embeddings/
|   |── generation/
│   ├── indexing/
│   ├── retrieval/
│   ├── vectorstores/
│   ├── test_config.py
│   └── test_health.py
├── .env.example
├── pyproject.toml
└── README.md
```

## Documentation

Initial project documentation is stored in `docs/design/`.

Current documents include:

* Project vision and goals
* High-level architecture
* API Design (draft)
* Implementation roadmap

The implemented `/v1/search` contract is documented in `docs/design/003-api-design.md` and in FastAPI's generated OpenAPI documentation. Additional design sections will be written and expanded as their implementation phases begin.

## License

This project is licensed under the MIT License.
