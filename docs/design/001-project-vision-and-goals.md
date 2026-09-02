# Project vision and goals

## Vision

The goal of this project is to build a lightweight, platform-agnostic Retrieval-Augmented Generation (RAG) service that demonstrates the core components of a modern retrieval system and the engineering decisions behind it.

The service is designed to separate content ingestion, retrieval, and answer generation into well-defined components rather than coupling them to a specific content management system or user interface. WordPress is the first content source and the first client application. The core retrieval engine remains reusable with other platforms through additional connectors, and reusable across WordPress sites through connector profiles.

This project is intended to be both a functional application and a reference implementation. In addition to working software, it includes architecture documentation, API documentation, and design rationale that explain why each major decision was made.

## Project goals

The primary goals of the project are to:

- Build a platform-agnostic Python RAG service that can index and retrieve documentation content.
- Keep WordPress-specific ingestion reusable, with site-specific behavior isolated in connector profiles.
- Design a small, well-defined REST API consisting of two public capability endpoints and one operational endpoint:

  - `POST /v1/search`
  - `POST /v1/answer`
  - `GET /health`
- Protect the capability endpoints with shared API-key authentication while leaving `/health` unauthenticated.
- Implement a complete indexing pipeline, including content retrieval, normalization, heading-aware chunking, embedding generation, and vector storage.
- Implement a hybrid retrieval pipeline that combines semantic and keyword search, reranks candidates, and returns no results when the corpus does not support the query.
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
- Service-to-service API authentication
- Documentation architecture
- Content modeling
- Connector and site-profile architecture
- Retrieval-aware content preparation
- Chunking and metadata strategies
- Embedding and vector search workflows
- Hybrid retrieval, reranking, and support gating
- LLM grounding and citation validation
- Retrieval evaluation methodology
- Technical documentation and developer experience

The objective is not simply to build a working RAG application, but to demonstrate thoughtful architectural decisions, clear documentation, and an understanding of how retrieval systems should be designed and evaluated.

## Scope

The current system is a single end-to-end implementation with these boundaries:

- WordPress as the first content source, with selectable site profiles
- WordPress as the first client application
- Python as the RAG service
- Heading-aware chunking as the chunking strategy
- Hybrid retrieval: semantic vector search, BM25 over the saved chunk files, reciprocal rank fusion, Voyage reranking, and a query-level support gate
- Two public capability endpoints and one operational endpoint:

  - `POST /v1/search`
  - `POST /v1/answer`
  - `GET /health`
- Shared API-key authentication for Search and Answer
- Documentation-focused content

Heading-aware chunking is used because documentation is already organized into meaningful sections. Preserving headings and section boundaries gives each chunk useful context while providing a clear baseline that can later be compared with other chunking strategies.

The public API is limited to two capability endpoints because the system has two primary user-facing capabilities: retrieving relevant source content and generating a grounded answer from that content. `/health` is an operational liveness check, not a third RAG capability. Indexing and administrative operations remain internal so the public interface stays small, easier to secure, easier to document, and less tightly coupled to implementation details.

This scope remains intentionally limited. The service supports one source platform, a small public API, and service-to-service authentication rather than user accounts. Hybrid retrieval and reranking are part of the current system; additional content platforms, query rewriting, and agentic workflows are not.

## Non-goals

The project intentionally does not attempt to:

- Support multiple CMS platforms or non-WordPress content sources.
- Include query rewriting or agentic retrieval workflows.
- Train or fine-tune language models.
- Build a production-scale authentication or user management system.
- Develop a custom embedding model or vector database.
- Build a polished, feature-rich search interface.
- Optimize for large-scale production deployment.

These capabilities remain future enhancements rather than current requirements.

## Why Python instead of a WordPress plugin?

Although the first implementation integrates with WordPress, the retrieval engine itself is intentionally implemented as an independent Python service rather than a WordPress plugin.

This separation provides several advantages:

- The core retrieval engine remains independent of any CMS.
- Additional connectors can be added without modifying retrieval logic.
- Another WordPress site can be configured through a profile without modifying the generic WordPress connector.
- Multiple client applications can share the same retrieval service.
- Python provides access to mature AI, embedding, and vector search libraries.
- An API-first architecture makes the system easier to test, document, and extend.

WordPress is treated as the first connector and the first client, not as the foundation of the retrieval engine itself. Things that are true of WordPress belong in the WordPress connector. Things that are true only of one WordPress site belong in that site's profile. This keeps content retrieval, site interpretation, retrieval logic, and presentation concerns independent while making the overall architecture easier to evolve over time.
