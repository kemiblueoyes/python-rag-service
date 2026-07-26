# API design

## Overview

The service exposes two public endpoints:

* `POST /v1/search`
* `POST /v1/answer`

Indexing remains an internal operation and is not exposed through the public API.

## POST /v1/search

Retrieves relevant document chunks without generating an answer.

### Request

```json
{
  "query": "How does metadata improve retrieval?",
  "filters": {
    "site_id": "the-doc-landscape"
  },
  "limit": 5
}
```

### Response

```json
{
  "query": "How does metadata improve retrieval?",
  "results": []
}
```

## POST /v1/answer

Retrieves relevant chunks and generates a grounded answer with validated sources.

### Request

```json
{
  "query": "Why does inconsistent terminology cause retrieval failures?",
  "filters": {
    "site_id": "the-doc-landscape"
  }
}
```

### Response

```json
{
  "query": "Why does inconsistent terminology cause retrieval failures?",
  "answer": "",
  "sources": [],
  "sufficient_evidence": false
}
```
