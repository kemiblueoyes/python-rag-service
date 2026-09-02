# ADR-001: Canonical Document Model

## Status

Accepted

## Date

2026-08-09

## Context

The RAG service must support multiple content sources without coupling the retrieval pipeline to any specific platform.

The initial implementation uses WordPress as the first content connector, but WordPress-specific data structures should not become the internal representation used by downstream RAG components.

The service requires a stable intermediate format between content ingestion and retrieval processing.

The canonical document model provides this boundary by allowing connectors to translate source-specific content into a platform-neutral representation.

The model must support:

- Document identification
- Source identification
- Site identification
- Titles and URLs
- Document body content
- Content type
- Categories and tags
- Publication metadata
- Modification tracking

The model should contain only information required by the RAG pipeline and should avoid storing source-specific fields that do not have a broader purpose.

## Decision

Use a canonical document model as the internal representation for all content entering the RAG pipeline.

Each connector is responsible for mapping source-specific content into this model.

The canonical document model will include:

- `document_id`
- `source`
- `source_id`
- `title`
- `url`
- `body`
- `content_type`
- `document_role`
- `indexable`
- `metadata`
- `published_at`
- `modified_at`

All downstream processing operates on canonical documents rather than native source responses.

The model intentionally does not include WordPress-specific concepts such as:

- WordPress post IDs as the primary identifier
- ACF fields
- Yoast-specific structures
- WordPress API response formats

Source-specific metadata may be handled within the connector when needed for mapping, but it should not leak into the core RAG pipeline unless it represents a generally useful retrieval concept.

## Options Considered

### Process source-specific data throughout the RAG pipeline

Rejected.

Advantages:

- Requires less initial modeling
- Allows direct use of source API responses

Disadvantages:

- Couples the RAG service to individual platforms
- Makes additional connectors more difficult
- Spreads source-specific assumptions throughout indexing and retrieval logic

### Store all available source metadata in the internal model

Rejected.

Advantages:

- Preserves maximum source information
- Provides flexibility for future use

Disadvantages:

- Creates unnecessary coupling to source systems
- Makes the model harder to maintain
- Encourages downstream dependencies on source-specific fields

### Minimal platform-neutral canonical document model

Selected.

Advantages:

- Maintains a clear boundary between ingestion and retrieval
- Supports future connectors
- Keeps downstream components independent of content platforms
- Provides a stable contract between connectors and processing pipelines

## Consequences

### Positive

- The RAG pipeline remains platform-agnostic
- New connectors can be added without redesigning chunking, embedding, retrieval, or generation
- Content processing can be tested independently from source systems
- The internal data contract is easier to document and maintain

### Negative

- Connector implementations require an additional mapping step
- Some source-specific information may not be preserved unless it has retrieval value
- The model must evolve carefully as new sources are added

## Future Considerations

The canonical document model may expand if future retrieval capabilities require additional shared metadata.

Potential additions could include:

- Audience metadata
- Content relationships
- Language information
- Version information
- Document hierarchy

Any additions should be evaluated based on whether they provide value across multiple connectors rather than solving a single source-specific requirement.

Changes to the canonical document model should be treated as architectural decisions because they affect connector implementations and downstream processing components.
