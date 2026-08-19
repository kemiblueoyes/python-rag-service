# High-level architecture

## Architecture overview

The system consists of a platform-agnostic Python RAG service, a WordPress content connector, a WordPress client, external model services, and a vector database.

WordPress serves two separate roles in the initial implementation:

- It is the first content source indexed by the RAG service.
- It is the first client used to submit queries and display results.

These responsibilities remain separate. The WordPress connector retrieves and transforms content for indexing, while the WordPress client sends user queries to the public API and renders the responses. Neither component contains the core retrieval or answer-generation logic.

The Python service owns the shared RAG functionality, including:

- Content normalization
- Chunking
- Embedding generation
- Vector storage and retrieval
- Query processing
- Context assembly
- Answer generation
- Citation validation
- Evaluation support

This separation keeps the core system independent of WordPress. A future content source could be supported by adding another connector that produces the same canonical document model. A future application could use the service by calling the same public API.

The system supports two primary workflows:

1. Content indexing, which prepares source content for retrieval.
2. User query processing, which either returns relevant content or generates a grounded answer from that content.

## System diagram

### Content indexing

```text
WordPress
    |
    | WordPress REST API
    v
WordPress connector
    |
    | Canonical documents
    v
Content normalization and cleaning
    |
    v
Heading-aware chunking
    |
    v
Embedding generation
    |
    v
Vector database
```

### User query processing

```text
WordPress client
    |
POST /v1/search or
POST /v1/answer
    |
    v
Python RAG service
    |
Query validation and embedding
    |
    v
Vector database
    |
    v
Retrieval and ranking
    /             \
   /               \
/v1/search      /v1/answer
    |               |
    |         Context assembly
    |               |
    |         LLM generation
    |               |
    |        Citation validation
    |               |
    v               v
Search results  Grounded answer
       \          /
        \        /
            |
            v
    WordPress client
```

The indexing and query workflows share the vector database but otherwise serve different purposes. Indexing writes normalized content and embeddings to the database. Query processing reads from the database to find information relevant to a user's request.

## Component responsibilities

### WordPress content source

The initial content source is a WordPress site.

WordPress remains the source of truth for published articles and their associated metadata, including:

- Titles
- URLs
- Article bodies
- Categories
- Tags
- Publication dates
- Modification dates
- Content types
- Publication status

The RAG service does not become the authoritative content repository. It stores retrieval-ready representations derived from the source content.

### WordPress connector

The WordPress connector is part of the Python service's ingestion layer.

It is responsible for:

- Calling the WordPress REST API
- Retrieving eligible posts and pages
- Extracting relevant WordPress fields
- Mapping WordPress data into the canonical document model
- Identifying updated, deleted, or unpublished content

The connector does not clean, chunk, embed, retrieve, or generate answers. Its role ends after it produces a platform-neutral document.

Keeping connector logic separate prevents WordPress-specific structures from spreading through the rest of the application.

### Canonical document model

The canonical document model provides a standard representation for content entering the RAG system.

It includes fields such as:

- Document ID
- Source
- Site ID
- Title
- URL
- Body
- Content type
- Categories and tags
- Publication date
- Modification date

All later indexing stages work with this model rather than with native WordPress responses.

This boundary makes the service platform-agnostic. Future connectors for other content systems can map their source data into the same model without requiring changes to the chunking, embedding, retrieval, or generation pipelines.

### Content processing pipeline

The content processing pipeline transforms canonical documents into retrieval-ready chunks.

It is responsible for:

- Removing unsupported markup and unrelated content
- Preserving meaningful headings, paragraphs, and lists
- Normalizing formatting and spacing
- Dividing documents into coherent chunks
- Preserving heading hierarchy and document metadata
- Creating stable identifiers for documents and chunks

The first version uses heading-aware chunking because documentation headings already provide meaningful structural boundaries. This produces an understandable baseline while preserving the context needed to interpret each retrieved section.

Detailed cleaning and chunking behavior is defined later in the content indexing pipeline section.

### Embedding provider

The embedding provider converts document chunks and user queries into numerical vectors.

The same embedding model must be used for indexed chunks and incoming queries so that their vectors can be compared within the same semantic space.

The service interacts with the embedding provider through an internal abstraction rather than embedding provider-specific calls throughout the application. This allows the selected model or provider to change without redesigning the full retrieval pipeline.

### Vector database

The vector database stores:

- Chunk embeddings
- Chunk text
- Chunk and document IDs
- Titles
- Heading paths
- Source URLs
- Categories and tags
- Site and source identifiers
- Modification dates

It supports semantic similarity searches and metadata filtering.

The vector database is a derived index rather than the source of truth. Its contents can be recreated from the original content source by running the indexing pipeline again.

### Retrieval service

The retrieval service contains the shared logic used by both public endpoints.

It is responsible for:

- Validating the query and supported filters
- Generating the query embedding
- Searching the vector database
- Applying metadata filters
- Ranking candidate chunks
- Removing weak or duplicate results
- Returning the most relevant chunks

Both `/v1/search` and `/v1/answer` use this same retrieval service. The application does not maintain separate retrieval implementations for search and answer generation.

This shared design reduces duplicated logic and makes retrieval behavior easier to test and evaluate consistently.

### Answer generation service

The answer generation service is used only by `/v1/answer`.

It is responsible for:

- Selecting retrieved chunks for the model context
- Assigning stable source identifiers
- Constructing the prompt
- Calling the selected language model
- Parsing the structured model response
- Determining whether the retrieved evidence is sufficient
- Passing proposed citations to the validation layer

The model is instructed to answer only from the supplied context and to acknowledge when the available sources are insufficient.

### Citation validation

The citation validation layer verifies the model's proposed citations before the response is returned.

It confirms that:

- Each cited chunk was included in the retrieved context
- Each chunk ID exists
- Titles, headings, and URLs come from stored metadata
- The model has not invented or altered a source

Trusted source information is added by the application rather than accepted directly from model-generated links.

This design reduces the risk of fabricated citations and maintains traceability between generated claims and indexed content.

### Public API

The Python service exposes two public endpoints:

| Endpoint | Responsibility |
|---|---|
| `POST /v1/search` | Retrieve relevant document chunks without generating an answer. |
| `POST /v1/answer` | Retrieve relevant chunks and generate a grounded, cited answer. |

The API is intentionally limited to the system's two user-facing capabilities.

Indexing, connector execution, and other administrative operations remain internal. They may be run through a command-line interface, scheduled process, or protected administrative workflow rather than exposed as public endpoints.

This keeps the public API easier to secure, version, test, document, and maintain.

### WordPress client

The WordPress client provides the first user interface for the service.

It is responsible for:

- Accepting a visitor's query
- Choosing the search or answer experience
- Sending requests to the Python API
- Handling loading, empty, insufficient-evidence, and error states
- Displaying retrieved sections or generated answers
- Rendering trusted source links and citations

The client does not generate embeddings, search the vector database, or call the language model directly.

Requests that require credentials should pass through WordPress server-side code so that secrets are not exposed in browser JavaScript.

### Evaluation layer

Evaluation is treated as a supporting architectural capability rather than a final testing step.

The evaluation layer uses a maintained test dataset to measure:

- Whether the correct chunks are retrieved
- Where relevant chunks appear in ranked results
- Whether irrelevant or duplicate chunks are returned
- Whether generated answers are supported by the retrieved evidence
- Whether citations point to the correct sources
- Whether unsupported questions are handled appropriately

Retrieval and answer generation are evaluated separately so failures can be traced to the correct part of the system.

## Data flow

### Indexing data flow

During indexing, data moves through the system as follows:

1. The WordPress connector retrieves published content through the WordPress REST API.
2. The connector maps each post or page into the canonical document model.
3. The content processing pipeline cleans and normalizes the document.
4. The chunking component divides the document into heading-aware sections.
5. The embedding provider generates an embedding for each chunk.
6. The service stores the chunk, embedding, and associated metadata in the vector database.
7. When source content changes, the service replaces the affected document's existing chunks.
8. When content is deleted or unpublished, the service removes its chunks from the index.

### Search data flow

For a search request:

1. The WordPress client sends a query and optional filters to `POST /v1/search`.
2. The API validates the request.
3. The embedding provider generates a query embedding.
4. The retrieval service searches the vector database and ranks matching chunks.
5. The API formats the selected chunks as search results.
6. The WordPress client displays the titles, headings, excerpts, and trusted source links.

No language model is involved in this workflow.

### Answer data flow

For an answer request:

1. The WordPress client sends a query and optional filters to `POST /v1/answer`.
2. The API validates the request.
3. The shared retrieval service finds the most relevant chunks.
4. The answer generation service assembles the selected chunks into a structured context.
5. The service sends the context and instructions to the language model.
6. The model returns a proposed answer and source identifiers.
7. The citation validation layer checks the proposed citations against the retrieved chunks.
8. The API returns the grounded answer, validated source information, and evidence-sufficiency status.
9. The WordPress client displays the answer and linked sources.

## Architectural boundaries

The architecture maintains the following boundaries:

- Source connectors translate platform-specific content but do not contain RAG logic.
- The canonical document model separates source ingestion from downstream processing.
- Content processing is independent of the source connector.
- Retrieval logic is shared by both public endpoints.
- Answer generation builds on retrieval rather than implementing a separate search path.
- Citation metadata is controlled by the application rather than the language model.
- The WordPress client handles presentation but not retrieval or generation.
- The vector database is a rebuildable index, not the authoritative content store.

These boundaries are intended to make the system understandable, testable, and extensible without adding unnecessary complexity to the first implementation.

## Deployment view

At a high level, the initial deployment contains three separately managed systems:

1. The existing WordPress site, which hosts the source content and user interface.
2. The Python RAG service, which exposes the public API and runs the indexing and query pipelines.
3. The vector database, which stores retrieval-ready chunks and embeddings.

The Python service also communicates with external embedding and language-model providers unless local models are selected.

The exact hosting platform, vector database, embedding model, and language model are implementation choices documented separately. The architecture should not require a particular vendor for any of these services.
