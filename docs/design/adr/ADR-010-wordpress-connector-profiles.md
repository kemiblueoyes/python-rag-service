# ADR-010: WordPress Connector Profiles

## Status

Accepted

## Date

2026-09-02

## Context

The RAG service uses a WordPress connector as its first content-source integration while keeping the core indexing, retrieval, and generation architecture platform-agnostic.

WordPress provides a common REST API and standard content fields, but individual WordPress installations frequently introduce their own conventions, including:

- Custom fields exposed through ACF or WordPress REST metadata
- Site-specific codes and labels
- Custom meanings for page hierarchies
- Site-specific document roles and relationships
- Custom HTML components that require special processing
- Sections that should be excluded from retrieval content

The initial WordPress implementation needed to understand The Doc Landscape. That site uses custom audience fields, AEO fields, series landing pages, nested series relationships, accordion blocks, and related-content sections. Placing those assumptions directly in the reusable WordPress client, mapper, or connector would make the connector appear generic while still coupling it to one site.

Creating a completely separate connector for every WordPress installation would avoid mixing site rules, but it would duplicate standard WordPress retrieval and mapping behavior.

The WordPress architecture therefore needed to:

- Keep behavior that is generally true of WordPress in the reusable connector layer
- Isolate assumptions that are true only of one WordPress installation
- Allow a site to use the connector without defining any custom behavior
- Support custom metadata mappings without expanding the canonical document model for every source field
- Allow complex site relationships to be added after standard mapping
- Pass site-specific HTML preservation and section-exclusion rules to the generic processing pipeline
- Let another WordPress site add its own behavior without modifying the generic connector
- Keep site-specific code out of the platform-neutral RAG pipeline

## Decision

Introduce configurable WordPress connector profiles that separate reusable WordPress behavior from site-specific interpretation.

The architectural rule is:

> Behavior that is generally true of WordPress belongs in the WordPress connector. Behavior that is true only of one WordPress installation belongs in that site's profile.

The reusable WordPress layer remains responsible for:

- Calling configured WordPress REST API collections
- Validating WordPress response records
- Mapping standard WordPress fields into canonical documents
- Extracting supported Yoast schema metadata when available
- Setting standard document identifiers, source values, content types, timestamps, roles, and indexability
- Recording immediate WordPress parent-page relationships

REST collections, including custom post types exposed by a site, remain runtime configuration through `WORDPRESS_COLLECTIONS`. A profile interprets retrieved records; it does not replace the WordPress client or determine how the REST API is called.

A `WordPressConnectorProfile` may provide:

- Metadata mappings from ACF or WordPress `meta` fields into canonical document metadata
- Optional value-to-label mappings while preserving scalar or list value shapes
- Document enrichers that add site-specific metadata, relationships, or document roles
- WordPress block classes that the processing pipeline must preserve intact
- Section headings that the processing pipeline should exclude from retrieval content

The connector first performs standard WordPress mapping and parent-relationship enrichment. It then runs the selected profile's document enrichers. The indexing command passes the profile's HTML-preservation and section-exclusion settings to the generic processing pipeline.

Profiles are registered by name and selected through the `WORDPRESS_PROFILE` environment setting.

The built-in `default` profile contains no site-specific mappings, enrichers, preserved block classes, or excluded headings. It allows ordinary WordPress posts and pages to use the generic behavior without adopting assumptions from The Doc Landscape.

The built-in `doc_landscape` profile demonstrates site-specific behavior. It:

- Maps The Doc Landscape ACF fields into canonical metadata
- Translates audience codes into readable labels while retaining the original codes
- Interprets selected page hierarchies as series landing pages and series articles
- Adds series metadata and document roles
- Preserves `wp-block-accordion` components during HTML processing
- Excludes the `Related Terms` and `Related Content` sections from retrieval content

Site profiles live under the profiles package rather than inside the reusable WordPress connector package. A new profile is created as a `WordPressConnectorProfile`, registered in the WordPress profile registry, and selected by configuration.

Profiles may adapt ingestion and processing behavior, but they must not perform chunking, embedding, vector storage, retrieval, reranking, or answer generation.

## Options Considered

### Put site-specific behavior in the generic WordPress connector

Rejected.

Advantages:

- Fewer modules and configuration choices
- Fastest way to support the first WordPress site
- Direct access to WordPress records during mapping

Disadvantages:

- Couples the connector to The Doc Landscape
- Makes custom field names and site conventions appear universally meaningful
- Requires modifying reusable connector code for every new WordPress site
- Makes generic behavior and site behavior difficult to test independently
- Weakens the platform-agnostic purpose of the connector architecture

### Create a separate connector for each WordPress site

Rejected.

Advantages:

- Keeps each site's assumptions isolated
- Allows unrestricted customization for each integration

Disadvantages:

- Duplicates WordPress REST retrieval, validation, and standard mapping logic
- Makes fixes to common WordPress behavior harder to apply consistently
- Treats site configuration differences as separate source-platform integrations
- Increases maintenance as additional WordPress sites are added

### Support only external declarative field configuration

Considered but not selected as the complete solution.

Advantages:

- Allows simple field mappings without writing Python code
- Could make basic profiles easier to create and validate
- Keeps customization mostly data-driven

Disadvantages:

- Does not cleanly express complex relationships such as nested series membership
- Cannot easily apply site-specific document roles based on multiple records
- Is insufficient for custom processing behavior such as preserved HTML components
- Would either limit profiles to simple cases or require an increasingly complex configuration language

### Use a reusable connector with selectable site profiles

Selected.

Advantages:

- Preserves one implementation of common WordPress behavior
- Keeps site-specific knowledge outside the generic connector
- Provides an empty default for ordinary WordPress sites
- Supports both simple metadata mapping and more complex enrichment functions
- Allows the generic processing pipeline to receive site-specific policies without containing site-specific code
- Makes site behavior explicit, selectable, and independently testable
- Allows another WordPress site to be added without changing downstream RAG components

Disadvantages:

- Adds another abstraction and configuration choice to the ingestion workflow
- Profiles that use enrichers require Python code and registration
- Powerful enrichers can become difficult to reason about if their responsibilities are not kept narrow
- Profile changes can alter canonical metadata or chunk output and may require re-indexing

## Consequences

### Positive

- The WordPress connector is reusable across sites with different content models and conventions.
- The default profile does not inherit The Doc Landscape assumptions.
- The Doc Landscape behavior is explicit instead of hidden inside generic mapping code.
- Common WordPress retrieval and mapping logic remains centralized.
- Custom fields can be preserved as flexible canonical metadata without changing the canonical document schema.
- Standard WordPress parent relationships and site-specific relationship meanings remain distinct.
- Site-specific HTML and section policies can influence generic processing through configuration.
- Connector, profile, and downstream RAG behavior can be tested separately.
- Adding a profile does not require changes to chunking, embedding, vector storage, retrieval, or generation interfaces.

### Negative

- Developers must understand the difference between connector configuration, collection configuration, and profile behavior.
- Each code-based profile must be implemented, registered, selected, documented, and tested.
- Document enrichers receive both raw WordPress records and mutable canonical documents, so poorly scoped enrichers could introduce hidden side effects.
- Changes to metadata mappings, document roles, preserved blocks, or excluded sections can change indexed output and require a rebuild.
- The current registry is static; adding a profile requires a code change rather than only deployment configuration.
- The abstraction has been demonstrated with a default profile and The Doc Landscape but has not yet been validated against several unrelated WordPress sites.

### Future Considerations

Add a second independently designed WordPress profile to validate that the abstraction captures common site-variation needs without leaking new assumptions into the connector.

Profile changes that affect canonical documents or processed content should trigger a full indexing review and, when necessary, a vector-index rebuild.

Future improvements may include:

- Validation for duplicate or conflicting metadata mappings
- Profile version identifiers recorded with indexing artifacts
- A plugin or discovery mechanism that avoids editing a central registry
- Declarative configuration for profiles that require only simple mappings
- Clearer safeguards or return-value contracts for document enrichers
- Tests that confirm site-specific rules do not affect the default profile

Custom post-type collection selection should remain separate from profile interpretation unless repeated site configurations show that bundling them provides a clearer operational model.

A profile should not become an escape hatch for source behavior that is broadly applicable to WordPress or for RAG behavior that belongs downstream. If a customization requires a fundamentally different source API or lifecycle, it should be evaluated as a separate connector rather than forced into a WordPress profile.
