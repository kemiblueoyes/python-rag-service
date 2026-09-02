# ADR-002: Connector Separation

## Status

Accepted

## Date

2026-08-09

Amended 2026-09-02 to record the generic WordPress connector / site-profile split.

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

The first WordPress connector also mixed two different kinds of knowledge: behavior that is generally true of WordPress, and behavior that is true only of The Doc Landscape. Custom ACF fields, audience-code translations, series parent/child semantics, glossary-specific assumptions, and accordion-block handling made the connector partly a site connector. That undermined the platform-agnostic goal at a finer grain: another WordPress site could not reuse the connector without inheriting Doc Landscape assumptions or forking the mapping logic.

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

## Later refinement (2026-09-02)

The connector remains separated from the core RAG engine. A second boundary was added *inside* the WordPress connector layer:

```text
Source-specific        Site-specific
RAG engine ← WordPress connector ← WordPress profile
```

Things that are true of WordPress belong in the WordPress connector. Things that are true only of one WordPress site belong in that site's profile.

The generic connector retrieves configured REST collections, maps standard WordPress fields, and records ordinary parent-page relationships. It does not encode one site's custom metadata, value translations, document roles, or HTML components.

A profile supplies everything specific to a particular WordPress installation:

- Custom metadata mappings (for example ACF or meta fields)
- Value translations (for example audience codes such as TW)
- Site-specific document relationships and roles (for example series landing pages)
- HTML components that must be preserved intact (for example wp-block-accordion)
- Site-specific processing hints (for example headings to exclude)
- The included doc_landscape profile therefore means: for this WordPress site, here is what these ACF fields mean, here is how audience codes should be translated, here is how series relationships work, and preserve these accordion blocks.

Another WordPress site can use the default profile or add its own profile without modifying the reusable WordPress client, mapper, or connector.

This refinement does not change the original rule that connectors must not clean content, chunk documents, embed, retrieve, or generate answers. Profiles still produce canonical documents. They configure mapping and enrichment at the connector boundary; they do not move site logic into the RAG pipeline.

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

### Site-specific WordPress logic embedded in the generic connector

Rejected.

Advantages:

- Faster for the first WordPress site
- Avoids an extra configuration object

Disadvantages:

- Turns the WordPress connector into a Doc Landscape connector
- Forces later WordPress sites to inherit or fork site-specific mapping
- Mixes platform knowledge with installation knowledge
- Makes the connector harder to test as a reusable component


## Consequences

### Positive

- The core RAG pipeline remains independent from WordPress
- Future content sources can be added through new connectors
- Content processing, retrieval, and generation can be tested independently from ingestion
- Source-specific changes remain isolated
- Another WordPress site can be configured through a profile without changing the generic WordPress client, mapper, or connector
- Site-specific custom fields, hierarchy semantics, and HTML behavior stay isolated from reusable WordPress ingestion
- The original platform-agnostic goal now holds at two levels: source platform vs RAG engine, and WordPress-in-general vs one WordPress site

### Negative

- Introduces an additional abstraction layer
- Requires each connector to implement document mapping logic
- Initial implementation requires more design work than directly processing WordPress responses
- WordPress ingestion now has two configuration surfaces (connector + profile), so ownership of a behavior must be decided before it is implemented

## Future Considerations

Additional connectors may be added in the future for other documentation platforms or content sources.

Each connector should:

- Retrieve source content
- Map content into the canonical document model
- Preserve required metadata
- Avoid implementing RAG-specific behavior

Connector additions should not require changes to chunking, embedding, retrieval, or answer-generation components.

When adding WordPress behavior, first decide whether it is true of WordPress generally or true of one site. General behavior belongs in the connector. 
Site behavior belongs in a profile.

Additional WordPress sites should be supported by adding or selecting a profile, not by specializing the generic connector.

A new content *platform* still requires a new connector. A new WordPress *site* should not.