# Python RAG Service

A platform-agnostic Python service for indexing documentation, performing semantic search, and generating grounded answers with citations.

The first implementation uses The Doc Landscape WordPress site as both:

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

## Initial architecture

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

Set the WordPress site URL in `.env`:

```dotenv
WORDPRESS_BASE_URL=https://doclandscape.com
```
Also ensure `.env.example` contains that variable.

Retrieve WordPress content and generate canonical documents:

```bash
uv run python -m rag_service.commands.index_wordpress
```
The command writes the current canonical documents to data/wordpress-documents.json. Each run compares the current documents with the previous output and reports documents that are new, updated, unchanged, or removed.

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
├── data/
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
