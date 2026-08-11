# ADR-003: Heading-Aware Chunking Strategy

## Status

Accepted

## Date

2026-08-09

## Context

The RAG service retrieves document chunks rather than complete source documents. Chunk boundaries therefore affect how much meaning and structural context remain available when content is retrieved independently from the page where it originally appeared.

The initial content source is documentation-oriented HTML. Its headings already define meaningful conceptual sections, and the content-processing pipeline preserves structural elements such as paragraphs, lists, code blocks, quotes, tables, and selected source-specific HTML components.

The chunking strategy must:

- Preserve meaningful document structure
- Preserve heading hierarchy
- Produce chunks small enough for retrieval
- Avoid unnecessarily breaking structured content
- Remain deterministic and testable
- Remain independent of WordPress-specific markup
- Provide a simple baseline that can later be evaluated and improved

A heading boundary alone is not sufficient because individual sections can still become too large. A size-based fallback is therefore required within heading sections.

## Decision

Use heading-aware chunking with a deterministic size-based fallback.

The processing pipeline will:

1. Parse normalized document HTML into ordered, source-neutral content blocks.
2. Build sections from the active heading hierarchy.
3. Treat each heading section as a hard chunking boundary.
4. Group content blocks within a section until the configured size limit is reached.
5. Split oversized paragraph content using a whitespace-aware fallback.
6. Preserve structured blocks that should remain intact even when they exceed the configured size limit.

The default maximum chunk size is `2,000` characters.

Heading hierarchy is preserved as a `heading_path` on each resulting chunk. Heading levels are interpreted structurally rather than requiring every intermediate level to exist. For example, an `h4` following an `h2` is treated as a child of that `h2`.

Content before the first heading is retained with an empty heading path rather than discarded.

The following block types are atomic and are not split:

- Lists
- Code blocks
- Quotes
- Tables
- Preserved HTML components

If an atomic block exceeds the configured maximum size, it is emitted intact as an oversized chunk.

Oversized paragraphs are split at whitespace where possible. If an individual word exceeds the size limit, the fallback slices the word to enforce the configured bound.

The initial implementation does not add overlap between adjacent chunks.

Source-specific components remain outside the generic chunking logic. A connector can identify components that must be preserved as a single `html_block`; for example, the WordPress connector currently preserves accordion components this way.

Each chunk retains structural context needed by downstream retrieval, including:

- Heading path
- Section anchor
- Block types
- Structural block metadata
- Document metadata
- Source document identity and URL

## Options Considered

### Fixed-size chunking without structural boundaries

Rejected.

Advantages:

- Simple to implement
- Produces consistently bounded chunks

Disadvantages:

- Ignores meaningful documentation structure
- Can separate content from the heading that provides its context
- Can break lists, code blocks, tables, and other structured content
- Produces less interpretable chunk boundaries

### Heading-only chunking without a size fallback

Considered.

Advantages:

- Closely follows author-defined document structure
- Very simple and deterministic

Disadvantages:

- Large sections can produce excessively large retrieval units
- Chunk size depends entirely on source authoring patterns
- Provides no bound when a single section contains substantial content

### Semantic chunking

Considered for future evaluation.

Advantages:

- May identify conceptual boundaries that are not represented by headings
- Could improve chunk boundaries for weakly structured content

Disadvantages:

- Adds implementation and evaluation complexity
- Produces a less transparent initial baseline
- Is unnecessary for the first implementation because the initial documentation corpus already contains meaningful heading structure

### Heading-aware chunking with a size fallback

Selected.

Advantages:

- Uses existing documentation structure as the primary semantic boundary
- Preserves heading hierarchy for retrieval context
- Bounds ordinary chunk size without discarding structural meaning
- Keeps rich content blocks intact
- Produces deterministic and testable output
- Provides a clear baseline for later retrieval evaluation

## Consequences

### Positive

- Retrieved chunks retain the section hierarchy that explains where the content belongs
- Chunk boundaries generally follow author-defined conceptual boundaries
- Lists, code, quotes, tables, and preserved components remain intact
- The strategy remains source-neutral while allowing connectors to preserve special components
- Deterministic behavior makes indexing and retrieval experiments reproducible
- Heading paths and anchors provide useful context for search results and citations

### Negative

- Retrieval quality depends partly on the quality of the source heading structure
- Character count is only an approximation of eventual model token usage
- Atomic structured blocks may exceed the configured maximum size
- Oversized paragraphs can be split at boundaries that are structurally valid but not conceptually ideal
- Without overlap, related context on opposite sides of an internal size boundary is not repeated between chunks

## Future Considerations

Chunking behavior should be evaluated using the retrieval evaluation framework rather than assuming the initial settings are optimal.

Future experiments may evaluate:

- Different maximum chunk sizes
- Token-based rather than character-based limits
- Chunk overlap
- Semantic or hybrid chunking
- Content-type-specific chunking policies
- Parent-child retrieval strategies
- Additional structural block types
- Different handling for oversized tables or preserved components

The initial heading-aware strategy should remain the baseline against which later chunking changes are measured.
