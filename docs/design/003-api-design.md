# API design

## Overview

Both public endpoints are implemented:

* `POST /v1/search`
* `POST /v1/answer`

Both endpoints use the same shared retrieval service. The answer endpoint passes the ranked retrieval results into the answer-generation workflow for context assembly, grounded generation, evidence-sufficiency detection, and citation validation.

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
      "anchor": "metadata-filtering",
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
* `anchor` - Source heading anchor for the retrieved chunk's current heading. `null` when no heading anchor is available.
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

Retrieves relevant documentation through the shared retrieval service and generates a grounded answer using only the selected evidence.

The endpoint uses the same retrieval pipeline as `POST /v1/search`. Retrieved chunks are passed to the answer-generation service, which assembles the model context, generates a structured answer, validates citations, and determines whether the available evidence is sufficient.

### Request

```json
{
  "query": "Why does inconsistent terminology cause retrieval failures?",
  "filters": {
    "source": "wordpress"
  }
}
```

### Request fields

#### `query`

Required string containing the natural-language question.

Leading and trailing whitespace is removed. Empty or whitespace-only questions are rejected.

#### `filters`

Optional object used to restrict retrieval before answer generation.

The supported filters are the same as for `POST /v1/search`:

* `document_id`
* `source`
* `source_id`
* `content_type`

Each filter may contain either a single non-empty string or a list of non-empty strings.

The answer endpoint does not expose a retrieval `limit`. Retrieval depth for answer generation is controlled internally by the service.

### Successful response

Status: `200 OK`

```json
{
  "query": "Why does inconsistent terminology cause retrieval failures?",
  "answer": "Inconsistent terminology can make retrieval less reliable because the query and documentation may use different language for the same concept. [S1]",
  "sources": [
    {
      "citation_id": "S1",
      "chunk_id": "wordpress:page:1:chunk:0",
      "document_id": "wordpress:page:1",
      "title": "Retrieval Failures",
      "heading_path": [
        "Vocabulary mismatch"
      ],
      "anchor": "metadata-filtering",
      "excerpt": "Inconsistent terminology can make relevant content harder to retrieve.",
      "url": "https://example.com/retrieval-failures/"
    }
  ],
  "sufficient_evidence": true
}
```

Each source contains:

* `citation_id` - Request-local source identifier used by the generated answer, such as `S1`.
* `chunk_id` - Stable identifier for the supporting chunk.
* `document_id` - Stable identifier for the source document.
* `title` - Title of the source document.
* `heading_path` - Heading hierarchy containing the supporting chunk.
* `anchor` - Source heading anchor for the supporting chunk's current heading. `null` when no heading anchor is available.
* `excerpt` - Text of the supporting chunk.
* `url` - Trusted URL stored with the source document.

Only sources whose citations were validated are returned.

### Insufficient evidence

A valid request for which the indexed documentation does not provide enough evidence is not treated as an API error.

Status: `200 OK`

```json
{
  "query": "What are the tax laws for importing a car into Brazil?",
  "answer": "The available documentation does not provide enough information to answer this question.",
  "sources": [],
  "sufficient_evidence": false
}
```

The exact answer text is generated by the configured language model, but an insufficient-evidence response contains no source citations.

### Validation errors

Status: `422 Unprocessable Content`

Answer requests use the same standard validation-error structure as search requests.

Validation failures include:

* Missing or empty queries
* Unsupported filters
* Invalid filter values
* Unexpected request fields
* Supplying a retrieval `limit`

### Answer unavailable

Status: `503 Service Unavailable`

A valid answer request may fail if a dependency or internal answer-generation stage cannot complete the operation.

The API returns:

```json
{
  "error": {
    "code": "answer_unavailable",
    "message": "Answer generation is temporarily unavailable.",
    "details": []
  }
}
```

This response may represent failures during retrieval, language-model generation, context assembly, or citation validation.

Provider-specific exception details are not exposed through the public API.
