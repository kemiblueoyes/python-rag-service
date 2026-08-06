# Python RAG Service

A platform-agnostic Python service for indexing documentation, performing semantic search, and generating grounded answers with citations.

The first implementation uses WordPress as both:

* the initial content source
* the initial client application

The core retrieval and answer-generation logic remains independent of WordPress so that additional content sources and clients can be added later.

## Project status

Active development. See the implementation roadmap in `docs/design/007-implementation-roadmap.md`.

## Planned capabilities

The completed service will support two public endpoints:

* `POST /v1/search` - retrieve relevant documentation sections
* `POST /v1/answer` - generate a grounded answer with validated citations

Content indexing will run through an internal command or administrative process rather than a public endpoint.

## Architecture

The system will contain:

* a WordPress connector that retrieves and maps source content
* a canonical document model
* content normalization and heading-aware chunking
* embedding generation
* vector storage and semantic retrieval
* shared retrieval logic
* answer generation and citation validation
* a WordPress client for displaying search results and answers

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

## WordPress indexing

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

Retrieve WordPress content and generate canonical documents and retrieval-ready
chunks:

```bash
uv run python -m rag_service.commands.index_wordpress
```
The command writes canonical documents to `data/wordpress-documents.json` and
retrieval-ready chunks to `data/wordpress-chunks.json`. Each run compares the
current documents with the previous canonical output and reports documents that
are new, updated, unchanged, or removed. Only indexable content documents are
chunked; WordPress accordions are passed to the generic processing pipeline as
preserved HTML components.

### WordPress connector profiles

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
│       ├── commands/
│       ├── connectors/
│       │   └── wordpress/
│       ├── indexing/
│       ├── models/
│       ├── processing/
│       ├── profiles/
│       ├── retrieval/
│       └── config.py
├── tests/
│   ├── connectors/
│   ├── indexing/
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
* Implementation roadmap

Additional design sections will be written and expanded as their implementation phases begin.

## License

This project is licensed under the MIT License.
