# Why heading-aware chunking first

(draft only)

The planned chunking strategy is heading-aware chunking for the first version of the RAG service. It’s deliberately a simple, explainable baseline rather than a generic fixed-token splitter.

Concretely, the pipeline should:
- Preserve the document title
- Use the document’s heading hierarchy as the primary chunk boundaries
- Keep paragraphs and lists grouped under the heading they belong to
- Store the heading path with each chunk, such as ["Why retrieval fails", "Vocabulary mismatch"]
- Preserve chunk order/sequence
- Carry forward the document’s metadata, URL, document ID, categories/tags, etc.
- Create stable chunk IDs so chunks can be replaced cleanly when a source document changes.

Heading-aware chunking is used first because documentation is already organized into meaningful sections. Preserving headings and section boundaries gives each chunk useful context while providing a clear baseline that can later be compared with other chunking strategies.
