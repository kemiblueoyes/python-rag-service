# API design

## Overview

The service exposes two public endpoints:

* `POST /v1/search`
* `POST /v1/answer`

`POST /v1/search` is implemented.

`POST /v1/answer` will be implemented after the answer-generation service is complete.

Indexing remains an internal operation and is not exposed through the public API.

The API uses `/v1` versioning so future breaking changes can be introduced without changing the behavior of existing clients.

FastAPI generates the OpenAPI specification from the implemented request models, response models, routes, and documented error responses.

When the service is running locally:

* Interactive API documentation: `http://127.0.0.1:8000/docs`
* OpenAPI document: `http://127.0.0.1:8000/openapi.json`

## POST /v1/search

Retrieves documentation chunks ranked by semantic similarity without generating an answer.

The endpoint uses the shared retrieval service, which generates the query embedding, searches the configured vector database, applies metadata filters, removes duplicate and weak results, and preserves similarity ranking.

### Request

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

### Request fields

#### `query`

Required string containing the natural-language search query.

Leading and trailing whitespace is removed. Empty or whitespace-only queries are rejected.

#### `filters`

Optional object used to restrict semantic retrieval by stored metadata.

Supported filters are:

* `document_id`
* `source`
* `source_id`
* `content_type`

Each filter may contain either a single non-empty string:

```json
{
  "source": "wordpress"
}
```

or a list of non-empty strings:

```json
{
  "content_type": ["page", "post"]
}
```

Unsupported filter names are rejected.

#### `limit`

Optional integer specifying the maximum number of retrieval results.

The default is `5`.

The value must be at least `1`.

### Successful response

Status: `200 OK`

```json
{
  "query": "How does metadata improve retrieval?",
  "results": [
    {
      "chunk_id": "wordpress:page:142:chunk:4",
      "document_id": "wordpress:page:142",
      "title": "Metadata Strategy for AI Retrieval",
      "heading_path": [
        "Metadata filtering"
      ],
      "excerpt": "Metadata can narrow the documents considered during retrieval...",
      "url": "https://example.com/metadata-strategy/",
      "score": 0.87
    }
  ]
}
```

Each result contains:

* `chunk_id` - Stable identifier for the retrieved chunk.
* `document_id` - Stable identifier for the source document.
* `title` - Title of the source document.
* `heading_path` - Heading hierarchy containing the retrieved chunk.
* `excerpt` - Text of the retrieved chunk.
* `url` - Trusted URL stored with the source document.
* `score` - Semantic similarity score returned for the result.

Results are returned in similarity-ranked order after duplicate removal and minimum-score filtering.

A valid query for which no result meets the retrieval threshold returns `200 OK` with an empty `results` array:

```json
{
  "query": "Something unrelated",
  "results": []
}
```

An empty result set is not treated as an API error.

### Validation errors

Status: `422 Unprocessable Content`

Requests that do not conform to the public API schema return the standard error format:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [
      {
        "field": "filters.site_id",
        "message": "Extra inputs are not permitted"
      }
    ]
  }
}
```

Validation failures include:

* Missing or empty queries
* Limits below `1`
* Unsupported filters
* Invalid filter values
* Unexpected request fields

The `code` field is the stable machine-readable error identifier. Human-readable validation messages may vary.

### Retrieval unavailable

Status: `503 Service Unavailable`

A valid request may fail if a dependency required for retrieval cannot complete the operation, such as the embedding provider or vector database.

The API returns:

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

The retrieval layer translates dependency failures into a provider-neutral retrieval error before the API formats the public response.

## POST /v1/answer

**Status: Not yet implemented.**

This endpoint will retrieve relevant chunks through the same shared retrieval service and generate a grounded answer with validated source references.

The request and response contract will be finalized during the answer-generation and answer-API implementation phases.

Planned request:

```json
{
  "query": "Why does inconsistent terminology cause retrieval failures?",
  "filters": {
    "source": "wordpress"
  }
}
```

Planned response shape:

```json
{
  "query": "Why does inconsistent terminology cause retrieval failures?",
  "answer": "",
  "sources": [],
  "sufficient_evidence": false
}
```

## Error format

Public API errors use a common top-level structure:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Human-readable summary.",
    "details": []
  }
}
```

The standard structure allows clients to handle errors consistently without depending on exception types or provider-specific messages.

Additional error categories may be added as later phases introduce authentication, answer generation, rate limiting, and production-readiness controls.
