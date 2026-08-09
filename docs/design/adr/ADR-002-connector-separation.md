# ADR-001: Connector Separation

## Status

Accepted

## Date

2026-08-09

## Context

The RAG service is designed to be platform-agnostic while initially using WordPress as the first content source.

The system needs a way to retrieve content from external platforms without allowing platform-specific implementation details to spread throughout the retrieval pipeline.

The architecture requires connectors to translate source-specific content into a standard representation that the rest of the system can process.

The connector architecture must support:

- Retrieving content from external sources
- Mapping source-specific fields into a canonical document model
- Supporting future content sources without redesigning the RAG pipeline
- Keeping indexing, retrieval, and generation logic independent from source platforms

Without a connector boundary, WordPress-specific structures and assumptions would become coupled to content processing, embeddings, vector storage, retrieval, and answer generation.

## Decision

Separate content connectors from the core RAG engine.

The initial implementation will use a WordPress connector responsible only for retrieving WordPress content and converting it into the canonical document model.

The connector will:

- Call the WordPress REST API
- Retrieve eligible posts and pages
- Extract relevant source fields
- Map WordPress responses into canonical documents
- Identify updated, deleted, or unpublished content

The connector will not:

- Clean or normalize content
- Chunk documents
- Generate embeddings
- Store vectors
- Perform retrieval
- Generate answers

All downstream RAG components will operate on the canonical document model rather than source-specific formats.

Future connectors must produce the same canonical document format so that additional content sources can be added without changing the retrieval architecture.

## Options Considered

### Connector logic embedded throughout the RAG pipeline

Rejected.

Advantages:

- Simpler initial implementation
- Fewer abstraction layers

Disadvantages:

- Creates tight coupling between the RAG system and content platforms
- Makes future connectors difficult to add
- Spreads source-specific assumptions throughout the application
- Makes testing and maintenance more difficult

### WordPress-specific RAG implementation

Rejected.

Advantages:

- Faster initial development
- Could leverage WordPress-specific APIs directly

Disadvantages:

- Limits the service to WordPress
- Prevents demonstrating a reusable RAG architecture
- Requires redesign if another content source is introduced

### Separate connector layer with canonical document model

Selected.

Advantages:

- Keeps the RAG service platform-agnostic
- Allows additional connectors without changing core retrieval logic
- Creates clear ownership boundaries
- Improves testing and maintainability

## Consequences

### Positive

- The core RAG pipeline remains independent from WordPress
- Future content sources can be added through new connectors
- Content processing, retrieval, and generation can be tested independently from ingestion
- Source-specific changes remain isolated

### Negative

- Introduces an additional abstraction layer
- Requires each connector to implement document mapping logic
- Initial implementation requires more design work than directly processing WordPress responses

## Future Considerations

Additional connectors may be added in the future for other documentation platforms or content sources.

Each connector should:

- Retrieve source content
- Map content into the canonical document model
- Preserve required metadata
- Avoid implementing RAG-specific behavior

Connector additions should not require changes to chunking, embedding, retrieval, or answer-generation components.
