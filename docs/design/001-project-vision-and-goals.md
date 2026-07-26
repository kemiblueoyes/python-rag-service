# Project vision and goals

## Vision

The goal of this project is to build a lightweight, platform-agnostic Retrieval-Augmented Generation (RAG) service that demonstrates the core components of a modern retrieval system and the engineering decisions behind it.

The service is designed to separate content ingestion, retrieval, and answer generation into well-defined components rather than coupling them to a specific content management system or user interface. While the initial implementation uses WordPress as both the content source and client application, the core retrieval engine should be reusable with other platforms through additional connectors.

This project is intended to be both a functional application and a reference implementation. In addition to working software, it includes architecture documentation, API documentation, and design rationale that explain why each major decision was made.

## Project goals

The primary goals of the project are to:

- Build a platform-agnostic Python RAG service that can index and retrieve documentation content.
- Design a small, well-defined REST API consisting of two public endpoints:

  - `POST /v1/search`
  - `POST /v1/answer`
- Implement a complete indexing pipeline, including content retrieval, normalization, heading-aware chunking, embedding generation, and vector storage.
- Implement a retrieval pipeline capable of performing semantic search over indexed documentation.
- Generate grounded answers using retrieved context and verified citations.
- Evaluate retrieval quality separately from answer generation quality.
- Produce comprehensive developer and architecture documentation that explains both how the system works and why it was designed this way.
- Demonstrate documentation engineering practices alongside software engineering practices.

## Portfolio objectives

This project serves as a portfolio piece that demonstrates experience across several disciplines commonly found in AI and documentation engineering roles.

Specifically, it showcases:

- RAG system architecture
- Python application design
- REST API design
- Documentation architecture
- Content modeling
- Retrieval-aware content preparation
- Chunking and metadata strategies
- Embedding and vector search workflows
- LLM grounding and citation validation
- Retrieval evaluation methodology
- Technical documentation and developer experience

The objective is not simply to build a working RAG application, but to demonstrate thoughtful architectural decisions, clear documentation, and an understanding of how retrieval systems should be designed and evaluated.

## Scope

The first version focuses on a single end-to-end implementation:

- WordPress as the content source
- WordPress as the client application
- Python as the RAG service
- Semantic vector search
- Heading-aware chunking as the initial chunking strategy
- Two public API endpoints:

  - `POST /v1/search`
  - `POST /v1/answer`
- Documentation-focused content

Heading-aware chunking is used first because documentation is already organized into meaningful sections. Preserving headings and section boundaries gives each chunk useful context while providing a clear baseline that can later be compared with other chunking strategies.

The public API is limited to two endpoints because the system has two primary user-facing capabilities: retrieving relevant source content and generating a grounded answer from that content. Indexing and administrative operations remain internal so the public interface stays small, easier to secure, easier to document, and less tightly coupled to implementation details.

This scope is intentionally limited to establish a solid architectural and evaluation baseline before introducing more advanced retrieval techniques, additional connectors, or broader API capabilities.

## Non-goals

The initial version of the project intentionally does not attempt to:

- Support multiple CMS platforms or content sources.
- Implement hybrid or keyword-based retrieval.
- Include reranking, query rewriting, or agentic retrieval workflows.
- Train or fine-tune language models.
- Build a production-scale authentication or user management system.
- Develop a custom embedding model or vector database.
- Build a polished, feature-rich search interface.
- Optimize for large-scale production deployment.

These capabilities are considered future enhancements rather than requirements for the initial implementation.

## Why Python instead of a WordPress plugin?

Although the first implementation integrates with WordPress, the retrieval engine itself is intentionally implemented as an independent Python service rather than a WordPress plugin.

This separation provides several advantages:

- The core retrieval engine remains independent of any CMS.
- Additional connectors can be added without modifying retrieval logic.
- Multiple client applications can share the same retrieval service.
- Python provides access to mature AI, embedding, and vector search libraries.
- An API-first architecture makes the system easier to test, document, and extend.

WordPress is treated as the first connector and the first client, not as the foundation of the retrieval engine itself. This separation keeps content retrieval, retrieval logic, and presentation concerns independent while making the overall architecture easier to evolve over time.
