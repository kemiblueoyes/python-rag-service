# ADR-005: Select Embedding Provider

## Status

Accepted

## Date

2026-08-09

## Context

The RAG service requires an embedding provider to convert document chunks and user queries into vector representations for semantic retrieval.

The embedding provider must support:

- Document and query embeddings
- Consistent embeddings between indexing and retrieval
- Python integration
- Reasonable cost for development and portfolio-scale usage
- Replacement without redesigning the retrieval pipeline

The architecture requires that embedding provider-specific logic remain isolated behind an internal abstraction so that the selected provider can be changed without affecting the rest of the system.

## Decision

Use Voyage AI `voyage-4-lite` as the initial embedding model.

The service will access the embedding provider through an internal embedding provider abstraction rather than calling Voyage APIs directly throughout the application.

The initial implementation will provide:

- A Voyage embedding provider adapter
- Configuration for API credentials and model selection
- Support for generating embeddings for document chunks and user queries

## Options Considered

### Voyage AI `voyage-4-lite`

Selected.

Advantages:

- Designed for retrieval workloads
- Low cost
- Strong fit for semantic search
- Supports document and query embedding workflows
- Allows future model changes through the provider abstraction

### OpenAI `text-embedding-3-small`

Considered.

Advantages:

- Mature ecosystem
- Simple API
- Low cost

Disadvantages:

- Less retrieval-specialized compared with Voyage

### Cohere Embed

Considered.

Advantages:

- Strong retrieval capabilities
- Designed for RAG workloads

Disadvantages:

- Provides capabilities beyond the current project requirements

## Consequences

### Positive

- Low-cost semantic retrieval foundation
- Provider can be replaced without changing the retrieval architecture
- Clear separation between application logic and external model services

### Negative

- Initial implementation depends on an external embedding provider
- Changing embedding models later requires re-indexing existing content

### Future Considerations

Future embedding providers can be added by implementing the same internal abstraction.

Embedding model changes should be evaluated through the retrieval evaluation framework before replacing the production model.