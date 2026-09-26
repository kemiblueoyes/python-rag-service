# Python RAG Service

A platform-agnostic Python service for indexing documentation, performing hybrid retrieval, and generating grounded answers with citations.

The first implementation uses WordPress as both:

* the initial content source
* the initial client application

The core retrieval and answer-generation logic remains independent of WordPress so that developers can add other content sources and clients later.

## Project status

Active development. The project implements and tests the core indexing, hybrid-retrieval, grounded-answer-generation, WordPress client, and evaluation workflows.

The service can:

- retrieve WordPress documents, 
- normalize and chunk them, 
- generate Voyage embeddings, 
- maintain a Qdrant vector index, 
- perform BM25 lexical retrieval, 
- combine vector and lexical results with reciprocal rank fusion (RRF), 
- rerank candidates with Voyage, 
- and apply a query-level support gate before returning results.

The service implements `POST /v1/search` and `POST /v1/answer`. Tests cover both endpoints, and the generated OpenAPI specification includes them. Both endpoints use the same hybrid retrieval pipeline. The answer endpoint adds token-budgeted context assembly, grounded generation through OpenAI, evidence-sufficiency handling, citation-integrity validation, citation normalization, and trusted source references.

A WordPress reference client is also implemented and proxies browser requests through WordPress to the Python API. It provides user-facing Search and Ask workflows, loading and error states, insufficient-evidence handling, source links, heading-anchor links, and clickable inline citations.

The project includes a versioned evaluation framework for retrieval and generated answers. The current dataset contains 22 cases covering answerable, expected-empty, synonym, ambiguous, confusable, multi-section, and updated-content behavior.

The latest recorded Phase 10 baseline used dataset version 1.5. In that run, all 22 cases passed the automated answer checks, all 14 answerable cases passed the human qualitative review, and all 8 expected-empty queries were correctly rejected by the retrieval support gate. multi-section-001 remained a known retrieval-coverage limitation for a compound query.

These results describe the recorded evaluation baseline rather than a continuously enforced performance guarantee. Changes to the corpus, models, prompts, chunking strategy, or retrieval configuration can change the results.

See the implementation roadmap in `docs/design/004-implementation-roadmap.md`.

## Current capabilities

### Ingestion and indexing

* WordPress REST API connector with configurable site profiles
* Platform-neutral canonical document model
* HTML cleanup and heading-aware chunking
* Stable document and chunk identifiers
* Voyage AI document and query embeddings
* Qdrant vector and chunk-metadata storage
* Full vector-index rebuilds
* Incremental handling of new, updated, unchanged, and removed documents

### Retrieval

* BM25 lexical retrieval over the indexed chunk corpus
* Vector retrieval through Qdrant
* Reciprocal rank fusion of lexical and vector candidates
* Voyage `rerank-2.5` reranking
* Query-level retrieval support gate for unsupported questions
* Query validation and supported metadata filtering
* Duplicate removal within each retriever's candidate list
* Configurable vector, lexical, and fused candidate depths
* Retrieval-service factory for application-wide dependency wiring
* Shared hybrid retrieval service used by both public endpoints

### Public API

* Public `POST /v1/search` endpoint
* Public `POST /v1/answer` endpoint
* Operational `GET /health` endpoint (liveness check)
* Explicit search and answer request/response schemas
* Empty search results and insufficient-evidence answers for unsupported questions
* Standard API error responses for validation, retrieval, and answer-generation failures
* FastAPI-generated OpenAPI and interactive API documentation for both endpoints

### Answer generation

* Configurable context-token budget with complete chunks preserved in retrieval order
* Request-local source identifiers such as `S1`, `S2`, and `S3`
* Provider-neutral prompt, token-counter, language-model, lexical-retrieval, and reranking interfaces
* OpenAI Responses API integration with structured Pydantic output
* Grounded-answer prompt that treats retrieved content as evidence rather than instructions
* Grounded-answer responses with validated source references
* Evidence-sufficiency detection with consistent citation requirements
* Citation-integrity validation for inline and structured citation identifiers
* Answer-generation factory for application-wide dependency wiring
* Final citation identifiers normalized by first appearance in the generated answer

### WordPress client

* WordPress reference client for `POST /v1/search` and `POST /v1/answer`
* Server-side WordPress REST proxy between the browser and Python API
* Search and Ask interface exposed through a WordPress shortcode
* Loading, disabled-button, empty-result, insufficient-evidence, and service-error states
* Search-result excerpts with configurable client-side truncation
* Links to source documents and retrieved heading anchors
* Safe rendering of generated paragraphs, lists, and bold text
* Clickable inline citations mapped to validated sources
* Responsive desktop and mobile client layout

### Evaluation and verification

* API tests for successful, empty-result, validation-error, service-unavailable, and OpenAPI behavior
* Live embedding, storage, retrieval, reranking, and filtering checks
* Live end-to-end verification through both public API workflows
* Live end-to-end answer-generation smoke test with a reviewable Markdown report
* Versioned retrieval and answer evaluation dataset
* Automated retrieval metrics and expected-empty evaluation
* Deterministic answer-structure and citation evaluation
* Human qualitative answer evaluation for support, completeness, unsupported details, and focus
* JSON and Markdown evaluation artifacts

## Public API

The service is intentionally designed around two public endpoints:

| Endpoint | Status | Purpose |
|---|---|---|
| `POST /v1/search` | Implemented | Retrieve relevant documentation chunks without generating an answer. |
| `POST /v1/answer` | Implemented | Retrieve relevant documentation and generate a grounded answer with validated sources. |

Both endpoints use the same retrieval pipeline. `POST /v1/answer` retrieves a fixed set of 5 chunks, then runs the grounded answer-generation and citation-validation workflow.

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
      "chunk_id": "wordpress:page:15:chunk:v1:<sha256>",
      "document_id": "wordpress:page:1",
      "title": "Metadata Strategy",
      "heading_path": ["Metadata filtering"],
      "anchor": "metadata-filtering",
      "excerpt": "Metadata can narrow the documents considered during retrieval.",
      "url": "https://example.com/metadata",
      "score": 0.91
    }
  ]
}
```

A valid query if the reranked result set doesn't pass the configured retrieval support gate, the endpoint returns `200 OK` with an empty `results` array.

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

If retrieval can't complete because a required dependency such as the embedding provider or vector database is unavailable, the API returns `503 Service Unavailable`:

```json
{
  "error": {
    "code": "retrieval_unavailable",
    "message": "Search is temporarily unavailable.",
    "details": []
  }
}
```

Provider-specific exception details aren't exposed through the public API.

### `POST /v1/answer`

The answer endpoint accepts a natural-language query and optional metadata filters. It does not accept a `limit` field. Extra fields, including `limit`, are rejected with `422 Unprocessable Content` and the `validation_error` response shown above.

The route always retrieves 5 chunks through the same hybrid retrieval pipeline as search, then runs grounded answer generation and citation validation.

If retrieval, the language model, the context budget, or citation validation fails, the API returns `503 Service Unavailable`. It does not return `retrieval_unavailable`:

```json
{
  "error": {
    "code": "answer_unavailable",
    "message": "Answer generation is temporarily unavailable.",
    "details": []
  }
}
```

Both endpoints require an `X-API-Key` header. A missing or wrong key returns `401` with `authentication_failed`. If `RAG_API_KEY` is unset, both endpoints return `503` with `authentication_unavailable`.

See `docs/design/003-api-design.md` for the current API contract.

## Architecture

The implemented system includes:

* a WordPress connector that retrieves and maps source content
* a platform-neutral canonical document model
* content normalization and heading-aware chunking
* embedding generation
* vector storage, BM25 lexical retrieval, RRF, Voyage reranking, and query-level support gating
* shared retrieval logic with validation, filtering, ranking, duplicate removal, BM25 lexical retrieval, RRF, Voyage reranking, and query-level support gating
* public search and answer APIs
* token-budgeted context assembly that preserves ranked source order
* grounded prompt construction
* a provider-neutral language-model interface with an OpenAI adapter
* structured answer parsing and evidence-sufficiency detection
* citation-integrity validation against supplied context
* final citation normalization and source filtering
* an answer generator that coordinates the complete generation workflow
* a WordPress reference client that proxies Search and Ask requests to the Python service

The WordPress connector and WordPress client serve different responsibilities. The connector brings WordPress content into the RAG system for indexing. The client is a consumer of the public API and presents search results and generated answers to site visitors.

The connector, retrieval pipeline, API layer, answer-generation layer, and client remain separate so source-specific and client-specific behavior doesn't spread through the core RAG logic.

## WordPress client

The first reference client is a WordPress plugin located at:

```text
clients/wordpress/python-rag-service-client/
```

The plugin provides a Search and Ask interface through the shortcode:

```text
[python_rag_service]
```

The browser sends requests to WordPress REST endpoints rather than directly to the Python service:

```text
Browser
  → WordPress REST proxy
  → Python RAG API
  → retrieval and answer-generation services
```

This keeps the Python service URL and API key on the server side rather than exposing them in browser JavaScript.

Configure an API key in the Python service's `.env` file:

```dotenv
RAG_API_KEY=replace-with-a-long-random-value
```

Configure the Python service base URL and the same API key in WordPress, typically in `wp-config.php`:

```php
define(
    'RAG_SERVICE_API_BASE_URL',
    'https://your-rag-service.example.com'
);

define(
    'RAG_SERVICE_API_KEY',
    'replace-with-the-same-long-random-value'
);
```

The WordPress proxy sends the key to the Python service in the `X-API-Key` header. Search and Answer requests fail if either constant is missing or if `RAG_SERVICE_API_KEY` doesn't exactly match `RAG_API_KEY`.

After changing the reference client, deploy the complete updated `clients/wordpress/python-rag-service-client` plugin directory to the WordPress site's `wp-content/plugins` directory. Updating the Python service alone doesn't update the live WordPress proxy or UI.

The client currently supports:

* Hybrid search through `/v1/search`
* Grounded questions through `/v1/answer`
* Loading states and duplicate-submission prevention
* Empty-result and insufficient-evidence states
* Normalized public error messages
* Truncated search excerpts
* Source-document and heading-anchor links
* Formatted generated answers
* Clickable inline citations and validated source lists
* Responsive desktop and mobile layouts

The included plugin is a reference implementation of a WordPress client rather than a general-purpose configurable WordPress product. The Python API remains platform-agnostic so developers can add other clients independently.

During local development, the Python API must be running and reachable from the hosted WordPress installation. A temporary HTTPS tunnel can provide that connection. Production deployment will replace the local server and development tunnel with an always-available hosted API.

That server-side proxy description matches the client currently committed: its WordPress routes call `RAG_SERVICE_API_BASE_URL`, authenticate with `RAG_SERVICE_API_KEY`, and forward Search and Answer requests to Python.


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

Set `RAG_API_KEY` to a long random value. Both `POST /v1/search` and `POST /v1/answer` require that value in the `X-API-Key` request header. The `/health` endpoint remains unauthenticated.

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

You can also use the interactive documentation to execute `POST /v1/search` against the configured retrieval service without using a terminal HTTP client.

## Indexing

### Provider configuration

The retrieval pipeline uses:

* [Voyage AI](https://www.voyageai.com/) for embeddings and reranking
* [Qdrant](https://qdrant.tech/) for vector storage and semantic retrieval
* BM25 for lexical retrieval over the local indexed chunk corpus
* RRF to combine vector and lexical candidates

Before indexing or running live retrieval, create a Voyage API key and configure Qdrant.

Configure the providers and retrieval pipeline in `.env`:

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

LEXICAL_CORPUS_PATH=data/wordpress-chunks.json
RETRIEVAL_VECTOR_CANDIDATE_DEPTH=20
RETRIEVAL_LEXICAL_CANDIDATE_DEPTH=20
RETRIEVAL_FUSED_CANDIDATE_DEPTH=20
RETRIEVAL_RRF_K=60
RETRIEVAL_SUPPORT_CUTOFF=0.70

RERANKING_PROVIDER=voyage
RERANKING_MODEL=rerank-2.5
```

`EMBEDDING_DIMENSION` must match the configured model's output. The default `voyage-4-lite` configuration produces 1,024-number vectors. The Qdrant adapter creates the collection and its required payload indexes when needed.

`LEXICAL_CORPUS_PATH` identifies the chunk corpus used for BM25 retrieval. The standard WordPress indexing workflow writes that corpus to `data/wordpress-chunks.json`.

The candidate-depth settings control how many results each retrieval stage considers before the pipeline returns the final results. The default pipeline retrieves up to 20 vector candidates and 20 BM25 candidates. It combines their rankings with RRF, keeps the top 20 fused candidates, and sends them to the configured reranker.

`RETRIEVAL_SUPPORT_CUTOFF` is a query-level support gate rather than a per-result similarity threshold. After reranking, if the highest rerank score is below `0.70`, the retrieval service returns no results. If the query passes the gate, the pipeline can return the requested number of reranked results.

We selected the `0.70` cutoff by evaluating the current corpus and models. Re-evaluate it if the corpus, embedding model, reranking model, chunking strategy, or retrieval configuration changes.

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
meaning of its page hierarchy. Every profile uses the shared mapper, which maps
standard WordPress fields and extracts supported Yoast schema metadata when
available. The connector records immediate page parent relationships.

### Initial vector-index build

Run a full rebuild to populate the Qdrant collection for the first time:

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

* The indexer processes, embeds, and stores new documents.
* The indexer removes old chunks from updated documents before storing current
  chunks.
* The indexer doesn't send unchanged documents to Voyage or rewrite them in
  Qdrant.
* The indexer removes all chunks for deleted or unpublished documents from
  Qdrant.

The indexer updates the local snapshot only after vector synchronization succeeds. If
Voyage or Qdrant fails, the next run can detect and retry the same changes.

The indexer chunks only indexable content documents. The active connector
profile passes configured WordPress accordions to the generic processing
pipeline as preserved HTML components.

### Live embedding and storage smoke test

The smoke test verifies one complete path through Voyage and Qdrant:

```text
sample chunk → document embedding → Qdrant storage
related question → query embedding → Qdrant search and filtering
```

Use a dedicated collection so test data can't mix with indexed documentation:

```dotenv
QDRANT_COLLECTION=rag_chunks_smoke_test
```

Then run:

```bash
uv run python -m rag_service.commands.smoke_embedding_storage
```

The command prints the retrieved title, text, similarity score, and filter
results. It intentionally leaves the test point in Qdrant for inspection. You
can delete the test collection from Qdrant after inspection. Restore
`QDRANT_COLLECTION=rag_chunks` before running WordPress indexing.

## Retrieval service

The shared retrieval service is the internal search pipeline used by both `POST /v1/search` and `POST /v1/answer`.

The current production pipeline is:

```text
Query
  ├─→ Voyage query embedding
  │     → Qdrant vector search
  │     → top vector candidates
  │
  └─→ BM25 lexical search
        → top lexical candidates

vector + lexical candidates
        ↓
reciprocal rank fusion
        ↓
top fused candidates
        ↓
Voyage rerank-2.5
        ↓
top rerank score below support cutoff?
  ├─ yes → return no results
  └─ no  → return requested reranked results
```

`RetrievalService`:

* validates non-empty queries and retrieval limits
* validates supported metadata filters
* generates a query embedding with the configured embedding provider
* retrieves semantic candidates from Qdrant
* retrieves lexical candidates with BM25
* removes duplicate chunks within each retriever's list
* combines vector and lexical rankings with RRF, keeping a chunk that appears in both lists so the overlap can raise its fused rank
* reranks fused candidates with the configured reranking provider
* applies the query-level support cutoff
* returns reranked results up to the requested limit

The current supported retrieval filters are:

* `document_id`
* `source`
* `source_id`
* `content_type`

A factory creates the retrieval service so both public API endpoints use the same configured embedding, vector, lexical, fusion, reranking, and support-gating pipeline.

The retrieval service rejects requests with a blank query, a limit below 1, an unsupported filter, or an invalid filter value before retrieval completes.

The support gate addresses a specific retrieval problem. A vector or lexical search will normally return the closest available content even when the corpus doesn't actually answer the user's question. Evaluation showed that neither raw vector similarity nor lexical matching alone provided a safe global cutoff. The current hybrid-and-reranking pipeline uses the top rerank score to decide whether the corpus provides enough retrieval support to return results.

### Live retrieval-service smoke test

The retrieval smoke test runs deliberately different queries against the indexed WordPress collection, including in-domain and out-of-domain questions.

Make sure `QDRANT_COLLECTION` points to the indexed documentation collection, then run:

```bash
uv run python -m rag_service.commands.smoke_retrieval_service
```

The command writes a reviewable Markdown report to:

```text
data/retrieval_smoke_results.md
```

The report includes each query, returned result count, rerank scores, titles, heading paths, URLs, chunk IDs, and chunk text. It records no qualifying results for unsupported queries that don't pass the support gate.

## WordPress connector profiles

WordPress installations commonly add custom post types, REST metadata, Advanced Custom Fields (ACF)
fields, and site-specific meanings for parent and child pages. Those decisions
belong in a connector profile rather than the reusable WordPress client,
mapper, or connector.

Define profiles with `WordPressConnectorProfile`. Each profile can provide:

* metadata mappings from either `acf` or WordPress `meta`
* optional value-label mappings
* document enrichers for site-specific relationships or roles
* HTML block classes that the processing pipeline must preserve intact
* headings whose sections are excluded from indexed chunks

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
configures The Doc Landscape's ACF fields, interprets selected parent pages
as series landing pages, and excludes the "Related Terms" and "Related Content"
sections from indexed chunks. Select it with:

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
added generic WordPress parent relationships. Keep them out of
`src/rag_service/connectors/wordpress/` unless the behavior applies broadly to
WordPress installations.

`preserved_block_classes` is also site-profile configuration. Use it for
components such as accordions or tabs that must remain a single HTML block
during parsing. The default profile preserves no special block classes.

`excluded_section_headings` names headings whose sections are dropped before
chunking. Matching is case-insensitive and applies to any heading in the
section path. The default profile excludes no headings.

## Answer generation

The internal answer-generation workflow accepts a question and ranked retrieval results, then:

1. Selects complete retrieved chunks within the configured context-token budget.
2. Assigns request-local source identifiers for the model context.
3. Constructs a grounded prompt containing the question and selected evidence.
4. Requests a structured answer from the configured language model.
5. Validates evidence sufficiency and citation integrity.
6. Keeps only sources cited by the generated answer.
7. Renumbers final citation identifiers sequentially by first appearance in the answer.

Configure answer generation in `.env`:

```dotenv
GENERATION_PROVIDER=openai
GENERATION_MODEL=gpt-5.6-terra
GENERATION_REASONING_EFFORT=low
GENERATION_CONTEXT_BUDGET_TOKENS=8000
GENERATION_MAX_OUTPUT_TOKENS=1000
OPENAI_API_KEY=your-openai-api-key
```

`GENERATION_CONTEXT_BUDGET_TOKENS` applies to the fully rendered evidence blocks. The workflow includes whole sources in retrieval order. It doesn't truncate chunks to fit the budget.

Citation identifiers such as `S1` and `S2` are local to one answer-generation request. Validation ensures that every citation refers to evidence supplied to the model. The final response then renumbers cited sources sequentially by first appearance so clients receive compact citation sequences without gaps.

### Live answer-generation smoke test

Configure the Voyage, Qdrant, and OpenAI credentials, and make sure `QDRANT_COLLECTION` points to the indexed documentation collection. Then run:

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

The report contains the question, generated answer, evidence-sufficiency result, validated source references, retrieval scores, and complete cited source text. It supports manual grounding review. The Evaluation section below describes automated structural evaluation and human qualitative answer evaluation.

## Evaluation

The project includes a versioned evaluation framework for testing retrieval and answer generation independently.

The project stores the baseline dataset at:

```text
evaluation/datasets/baseline.json
```

The current dataset contains 22 cases covering answerable and expected-empty queries as well as exact-answer, confusable, ambiguous, synonym, multi-section, and updated-content behavior.

The framework evaluates retrieval and answer quality separately because they measure different failures. A retrieval result set can miss part of the gold retrieval target while still providing enough evidence for a correct answer. Conversely, structurally valid retrieval and citations don't guarantee that a generated answer is complete and well focused.

Evaluation runs write JSON and Markdown reports to `data/evaluation/`. This directory contains generated local artifacts and isn't committed to the repository.

Evaluation results in this README and in docs/evaluation/ are recorded baseline results from completed evaluation runs. They are not continuously verified by the test suite or CI. Rerun the evaluation commands after changes that may affect retrieval or generation quality.

### Retrieval evaluation

Run the production retrieval pipeline against the gold dataset:

```bash
uv run python -m rag_service.commands.evaluate_retrieval
```

The command writes:

```text
data/evaluation/retrieval_baseline.json
data/evaluation/retrieval_baseline.md
```

The retrieval evaluator measures primary-source hits, precision, recall, reciprocal rank, expected-empty behavior, and overall case success.

In the recorded dataset `1.5` evaluation baseline, the production pipeline rejected all 8 expected-empty cases. The remaining known retrieval limitation was `multi-section-001`, a compound query where the top-five result set did not satisfy the benchmark's full primary-section coverage requirement. The remaining known retrieval limitation is `multi-section-001`, a compound query where the top-five result set doesn't satisfy the benchmark's full primary-section coverage requirement.

### Answer evaluation

Run live retrieval and grounded generation for the complete evaluation set:

```bash
uv run python -m rag_service.commands.evaluate_answers
```

The command writes:

```text
data/evaluation/answer_baseline.json
data/evaluation/answer_baseline.md
```

The deterministic evaluator checks:

* whether the system correctly identifies sufficient or insufficient evidence
* whether answerable responses include valid citations
* whether sufficient answers cite at least one primary source
* whether expected-empty responses avoid citations
* whether citations refer only to retrieval sources judged relevant for the case

In the recorded dataset `1.5` baseline, all 22 cases passed the structural checks, with 100% evidence-sufficiency accuracy and 100% citation-behavior accuracy.

### Human qualitative answer review

Answerable cases are also reviewed on four qualitative dimensions:

* **Support / faithfulness**: Whether meaningful claims match the retrieved evidence
* **Required-point completeness**: Whether the answer covers the important expected points
* **Unsupported details**:  Whether the answer adds claims not supported by retrieved evidence
* **Focus / relevance**: Whether the answer stays on the user's actual question

Reviewers score each dimension from `0` to `2`. A strict qualitative pass requires `2` on all four dimensions.

The project stores the current review in:

```text
data/evaluation/answer_qualitative_review.json
```

Generate the Markdown report with:

```bash
uv run python -m rag_service.commands.report_qualitative_answers
```

The command writes the report to:

```text
data/evaluation/answer_qualitative_review.md
```

In the recorded dataset `1.5` qualitative review, all 14 answerable cases received a strict pass, with an average score of `2.00 / 2` on all four dimensions.

The evaluation process also produced a prompt improvement. An earlier answer to `context-001` used the provided evidence but wandered into related AI-assistant material that wasn't needed to answer the question. The grounded-answer prompt now explicitly instructs the model to ignore source material that's related to the topic but unnecessary for the user's question.

For the detailed investigation that led from semantic-only retrieval to the current hybrid + reranking + support-gate design: 
- `docs/evaluation/retrieval-failure-analysis.md`: Investigation of retrieval failures and the experiments that led to the current pipeline
- `docs/evaluation/evaluation-summary.md`: Consolidated evaluation results, findings, and known limitations


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
├── clients/
│   └── wordpress/
│       └── python-rag-service-client/
│           ├── assets/
│           ├── includes/
│           └── python-rag-service-client.php
├── docs/
│   ├── design/
│   │   └── adr/
│   └── evaluation/
├── evaluation/
│   └── datasets/
├── src/
│   └── rag_service/
│       ├── api/
│       │   └── routes/
│       ├── commands/
│       │   └── documentation/
│       ├── connectors/
│       │   └── wordpress/
│       ├── embeddings/
│       ├── evaluation/
│       ├── generation/
│       │   └── providers/
│       ├── indexing/
│       ├── lexical/
│       ├── models/
│       ├── processing/
│       ├── profiles/
│       ├── reranking/
│       ├── retrieval/
│       ├── vectorstores/
│       └── config.py
├── tests/
│   ├── api/
│   ├── commands/
│   ├── connectors/
│   │   └── wordpress/
│   ├── embeddings/
│   ├── evaluation/
│   ├── generation/
│   ├── indexing/
│   ├── lexical/
│   ├── processing/
│   ├── reranking/
│   ├── retrieval/
│   ├── vectorstores/
│   ├── test_config.py
│   └── test_health.py
├── .env.example
├── pyproject.toml
└── README.md
```

## Documentation

Design records live in `docs/design/`.

Architecture decisions live in `docs/design/adr/` (ADR-001 through ADR-010). They cover the canonical document model, connector separation, heading-aware chunking, the two public API endpoints, the automation orchestration layer, Voyage embeddings, Qdrant, hybrid retrieval and reranking, API-key authentication, and WordPress connector profiles.

`docs/design/003-api-design.md` and FastAPI's generated OpenAPI documentation describe the implemented `/v1/search` and `/v1/answer` contracts.

Evaluation datasets live in `evaluation/datasets/` and generated evaluation artifacts live in `data/evaluation/`.

## License

The MIT License covers this project.
