# API design

## Overview

The public API exposes two user-facing capability endpoints and one operational endpoint:

* `POST /v1/search`
* `POST /v1/answer`
* `GET /health`

Search and Answer use the same shared retrieval service. That service combines semantic vector search, BM25 over the saved chunk files, reciprocal rank fusion, Voyage reranking, and a query-level support gate. The answer endpoint then passes any ranked results into the answer-generation workflow for context assembly, grounded generation, evidence-sufficiency detection, and citation validation.

`GET /health` is an operational liveness check. It is not a third RAG capability and is not versioned under `/v1`.

Indexing remains an internal operation and is not exposed through the public API.

The capability endpoints use `/v1` versioning so future breaking changes can be introduced without changing the behavior of existing clients.

Search and Answer require a shared API key. `/health` does not.

FastAPI generates the OpenAPI specification from the implemented request models, response models, routes, authentication scheme, and documented error responses.

When the service is running locally:

* Interactive API documentation: `http://127.0.0.1:8000/docs`
* OpenAPI document: `http://127.0.0.1:8000/openapi.json`

## Authentication

`POST /v1/search` and `POST /v1/answer` require the `X-API-Key` request header. The value must match the service's configured `RAG_API_KEY`.

This is service-to-service authentication. The key identifies a trusted client application, not an individual end user.

Trusted clients, including the WordPress server-side proxy, add the header when calling the Python API. Browser-delivered code should not include the key.

A missing or incorrect key returns `401 Unauthorized`:

```json
{
  "error": {
    "code": "authentication_failed",
    "message": "A valid API key is required.",
    "details": []
  }
}
```

If `RAG_API_KEY` is not configured on the server, the capability endpoints fail closed with `503 Service Unavailable`:

```json
{
  "error": {
    "code": "authentication_unavailable",
    "message": "API authentication is temporarily unavailable.",
    "details": []
  }
}
```

The service does not silently disable authentication when the key is missing.

`GET /health` remains unauthenticated so hosting and monitoring systems can confirm that the process is running without storing or sending a secret.

## GET /health

Confirms that the service process has started and can respond.

The endpoint does not retrieve content, generate answers, inspect indexes, or check external dependencies.

### Successful response

Status: `200 OK`

```json
{
  "status": "ok"
}
```

No request body or API key is required.

## POST /v1/search

Retrieves documentation chunks through the shared hybrid retrieval pipeline without generating an answer.

The endpoint validates the request, generates the query embedding, searches the vector database, searches the saved chunk files with BM25, removes duplicates, fuses the ranked lists, reranks the fused candidates, and applies the query-level support gate.

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

Optional object used to restrict retrieval by stored metadata.

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
* `score` - Rerank score returned for the result.

Results are returned in reranked order after fusion, duplicate removal, and the support gate.

A valid query that does not pass the retrieval support gate returns `200 OK` with an empty `results` array:

```json
{
  "query": "Something unrelated",
  "results": []
}
```

An empty result set is not treated as an API error. The support gate is applied to the query as a whole. If the highest rerank score is below the configured cutoff, no results are returned.

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

A valid request may fail if a dependency required for retrieval cannot complete the operation, such as the embedding provider, vector database, lexical index, or reranker.

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

The endpoint uses the same hybrid retrieval pipeline as `POST /v1/search`. Retrieved chunks are passed to the answer-generation service, which assembles the model context, generates a structured answer, validates citations, and determines whether the available evidence is sufficient.

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

A valid request for which the indexed documentation does not provide enough evidence is not treated as an API error. This includes queries rejected by the retrieval support gate and questions the language model cannot answer from the retrieved context.

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
