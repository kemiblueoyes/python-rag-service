# ADR-006: Select Vector Database

## Status

Accepted

## Date

2026-08-09

## Context

The RAG service requires a vector database to store and retrieve document chunks for semantic search.

The vector database is responsible for storing:

- Chunk embeddings
- Chunk text
- Chunk and document identifiers
- Titles
- Heading paths
- Source URLs
- Categories and tags
- Site and source identifiers
- Modification dates

The vector database must support:

- Semantic similarity search
- Metadata filtering
- Adding, updating, and deleting indexed chunks
- Re-indexing when source content changes
- A rebuildable retrieval index rather than acting as the source of truth

The architecture requires that vector database-specific logic remain isolated behind an internal abstraction so the storage technology can be replaced without redesigning the retrieval pipeline.

Future retrieval improvements may include hybrid search and reranking. The selected database should support these future capabilities without requiring changes to the core architecture.

## Decision

Use Qdrant as the initial vector database.

The service will access the vector database through an internal vector store abstraction rather than calling Qdrant APIs directly throughout the application.

The initial implementation will provide:

- A Qdrant vector store adapter
- Configuration for Qdrant connection details
- Storage and retrieval of document chunks and embeddings
- Metadata filtering support
- Upsert and deletion workflows for incremental indexing

## Options Considered

### Qdrant

Selected.

Advantages:

- Designed specifically for vector search workloads
- Strong metadata filtering capabilities
- Open-source with managed hosting available
- Simple local development using Docker
- Python-friendly ecosystem
- Supports future retrieval improvements such as hybrid search and external reranking workflows

Disadvantages:

- Requires managing more infrastructure decisions compared with fully managed alternatives

### Pinecone

Considered.

Advantages:

- Mature managed vector database service
- Simple operational model
- Strong metadata filtering
- Commonly used in production RAG systems

Disadvantages:

- Greater vendor dependency
- Less control over deployment compared with open-source alternatives

### Weaviate

Considered.

Advantages:

- Feature-rich retrieval platform
- Supports hybrid search and reranking workflows
- Open-source and managed options

Disadvantages:

- Provides capabilities beyond the initial requirements
- May introduce unnecessary complexity for the first implementation

### PostgreSQL with pgvector

Considered.

Advantages:

- Uses familiar relational database technology
- Low operational cost
- Natural metadata storage

Disadvantages:

- Less specialized as a dedicated vector retrieval system
- Less aligned with the architecture's separation of retrieval index from source content

### Chroma

Considered.

Advantages:

- Simple Python integration
- Good for experimentation and prototypes

Disadvantages:

- Better suited for prototypes than a portfolio-quality retrieval service architecture

## Consequences

### Positive

- Provides a production-oriented foundation for semantic retrieval
- Supports the current Phase 4 requirements without unnecessary complexity
- Allows future retrieval improvements such as reranking without changing the storage layer
- Keeps vector storage replaceable through an abstraction layer

### Negative

- The initial implementation depends on Qdrant-specific infrastructure
- Migrating to another vector database would require implementing another adapter and rebuilding the index

### Future Considerations

The vector database should continue to be evaluated separately from retrieval strategies.

Future improvements may include:

- Hybrid search
- Reranking
- Retrieval experimentation
- Additional vector database adapters

Changes to the vector database should be evaluated using the retrieval evaluation framework to ensure retrieval quality is maintained.