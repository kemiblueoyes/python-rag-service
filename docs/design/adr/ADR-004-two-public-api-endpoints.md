# ADR-004: Two Public API Endpoints

## Status

Accepted

## Date

2026-08-09

Amended 2026-09-02 to record `/health` as an operational endpoint.

## Context

The RAG service is designed as a reusable retrieval system rather than a
collection of individually exposed pipeline components.

Internally, the service contains multiple stages:

-   Content connectors
-   Canonical document processing
-   Content parsing
-   Chunking
-   Embedding generation
-   Vector indexing
-   Retrieval
-   Context assembly
-   Answer generation

These stages are implementation details that should remain independently
changeable.

The public API should expose useful capabilities to applications while
avoiding unnecessary coupling to internal architecture decisions.

The service needs to support two primary use cases:

1.  Applications that need retrieved knowledge units and want to control
    their own response generation.
2.  Applications that want a complete retrieval-augmented answer
    experience.

Operators and the host environment also need a way to confirm that the
service process is running. That check is an operational concern, not a
third RAG capability.

## Decision

Expose only two public user-facing capability API endpoints:

- `POST /v1/search`
- `POST /v1/answer`

The service will not expose internal pipeline operations as public
endpoints.

## Later refinement (2026-09-02)

The two user-facing capability endpoints remain `/v1/search` and
`/v1/answer`. `/health` was added as an operational endpoint, not as a
third application capability.

`/health` reports that the service process is running. It does not
retrieve content, generate answers, or expose internal pipeline stages.

Unlike the capability endpoints, `/health` is unauthenticated and is not
versioned under `/v1/`.

This does not change the original rule: the public API still does not
expose ingest, chunking, embedding, indexing, or generation as separate
endpoints.

## Endpoint Responsibilities

### `/search`

The `/search` endpoint provides retrieval-only functionality.

It returns relevant retrieved chunks and associated metadata without
generating a final answer.

This endpoint supports use cases such as:

-   Custom application experiences
-   Retrieval evaluation
-   Debugging retrieval quality
-   Citation workflows
-   Applications that use their own generation layer

The endpoint is responsible for retrieving relevant information, not
interpreting or generating responses.

### `/answer`

The `/answer` endpoint provides a complete retrieval-augmented
generation workflow.

It coordinates:

1.  Query processing
2.  Retrieval of relevant chunks
3.  Context assembly
4.  Response generation

This endpoint is intended for applications that need a complete
question-answering experience without implementing the retrieval
workflow themselves.

### `/health`

The `/health` endpoint is an operational liveness check.

It confirms that the service process has started and can respond. It is
not a retrieval, generation, or dependency-readiness API.

## Options Considered

### Expose every internal RAG stage as a public endpoint

Rejected.

Examples:

-   `/ingest`
-   `/chunk`
-   `/embed`
-   `/index`
-   `/retrieve`
-   `/generate`

Advantages:

-   Provides maximum flexibility
-   Makes individual stages directly accessible

Disadvantages:

-   Exposes implementation details
-   Creates API contracts around components that may change
-   Increases maintenance burden
-   Requires consumers to understand internal architecture

### Create one general-purpose endpoint that handles everything

Rejected.

Advantages:

-   Simple API surface
-   Easy for consumers to understand initially

Disadvantages:

-   Removes flexibility for retrieval-only use cases
-   Makes debugging and evaluation harder
-   Does not provide access to retrieved source material
-   Couples all consumers to one workflow

### Provide focused capability-based endpoints

Selected.

Advantages:

-   Keeps the public API simple
-   Separates retrieval from generation
-   Supports multiple application patterns
-   Allows internal architecture to evolve independently

## Consequences

### Positive

-   Consumers have a clear and understandable API surface
-   Retrieval can be evaluated independently from generation
-   Applications can choose between retrieval-only and full RAG
    workflows
-   Internal implementation details remain private
-   Future pipeline improvements do not require API changes
-   Operators can check process liveness without a third capability
    endpoint or an authenticated RAG call

### Negative

-   Some advanced consumers may need capabilities not exposed through
    the initial API
-   Additional endpoints may be required if future use cases emerge
-   The API must remain intentionally scoped to avoid exposing
    unnecessary internals

## Future Considerations

Additional endpoints should only be added when they represent stable
user-facing capabilities or operational needs, rather than internal
implementation steps.

Potential future additions may include:

-   Evaluation endpoints
-   Administrative indexing workflows
-   Readiness, metrics, or other observability endpoints
-   Configuration or management APIs

Any future endpoint should be evaluated against the same principle:

The API should expose what applications need to accomplish, not how the
RAG system internally accomplishes it.
