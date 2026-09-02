# High-level architecture

## Architecture overview

The system consists of a platform-agnostic Python RAG service, a WordPress content connector with selectable site profiles, a WordPress client, external model services, and a vector database.

WordPress serves two separate roles:

- It is the first content source indexed by the RAG service.
- It is the first client used to submit queries and display results.

These responsibilities remain separate. The WordPress connector retrieves and transforms content for indexing, while the WordPress client sends user queries to the public API and renders the responses. Neither component contains the core retrieval or answer-generation logic.

The Python service owns the shared RAG functionality, including:

- Content normalization
- Chunking
- Embedding generation
- Vector storage
- Lexical retrieval
- Hybrid fusion, reranking, and support gating
- Query processing
- Context assembly
- Answer generation
- Citation validation
- API authentication
- Evaluation support

This separation keeps the core system independent of WordPress. A future content source could be supported by adding another connector that produces the same canonical document model. Another WordPress site can be supported by adding or selecting a profile without changing the generic connector. A future application could use the service by calling the same public API.

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
    | optional site profile
    v
Canonical documents
    |
    v
Content normalization and cleaning
    |
    v
Heading-aware chunking
    |
    | Chunks
    +------------------+
    |                  |
    v                  v
Embedding          Saved chunk files
generation
    |
    v
Vector database
```

### User query processing

```text
WordPress client
    |
    | WordPress REST proxy
    | X-API-Key
    v
POST /v1/search or
POST /v1/answer
    |
    v
Python RAG service
    |
Query validation
    |
    +-- query embedding --> Vector database --> semantic candidates
    |
    +-- BM25 --> Saved chunk files --> lexical candidates
    |
    v
Fusion, reranking, and support gate
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

The indexing and query workflows share the derived retrieval indexes but otherwise serve different purposes. Indexing writes normalized chunks and embeddings to the vector database and writes the same chunks to saved chunk files for keyword search. Query processing reads both indexes, combines the ranked results, and either returns the selected chunks or generates a grounded answer.

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
- Retrieving configured REST collections
- Extracting standard WordPress fields
- Mapping WordPress data into the canonical document model
- Recording ordinary parent-page relationships
- Identifying updated, deleted, or unpublished content

The connector does not clean, chunk, embed, retrieve, rerank, or generate answers. Its role ends after it produces a platform-neutral document, optionally enriched by a site profile.

Keeping connector logic separate prevents WordPress-specific structures from spreading through the rest of the application.

### WordPress connector profiles

A profile supplies behavior that is true of one WordPress installation rather than of WordPress generally.

The architectural rule is:

> Things that are true of WordPress belong in the WordPress connector. Things that are true only of one WordPress site belong in that site's profile.

A profile may provide:

- Custom metadata mappings
- Value translations
- Site-specific document relationships and roles
- HTML components that must be preserved intact
- Section headings to exclude from retrieval content

The built-in `default` profile adds no site-specific behavior. The `doc_landscape` profile interprets The Doc Landscape's custom fields, audience codes, series relationships, and accordion blocks.

Another WordPress site can use the default profile or add its own profile without modifying the reusable WordPress client, mapper, or connector. Profiles still produce canonical documents. They do not move site logic into the RAG pipeline.

### Canonical document model

The canonical document model provides a standard representation for content entering the RAG system.

It includes fields such as:

- Document ID
- Source
- Source ID
- Title
- URL
- Body
- Content type
- Document role
- Indexability
- Flexible metadata
- Publication date
- Modification date

All later indexing stages work with this model rather than with native WordPress responses.

This boundary makes the service platform-agnostic. Future connectors for other content systems can map their source data into the same model without requiring changes to the chunking, embedding, retrieval, or generation pipelines. Site-specific fields belong in metadata or in a profile, not in the shared document schema.

### Content processing pipeline

The content processing pipeline transforms canonical documents into retrieval-ready chunks.

It is responsible for:

- Removing unsupported markup and unrelated content
- Preserving meaningful headings, paragraphs, and lists
- Normalizing formatting and spacing
- Dividing documents into coherent chunks
- Preserving heading hierarchy and document metadata
- Creating stable identifiers for documents and chunks

The pipeline uses heading-aware chunking because documentation headings already provide meaningful structural boundaries. This produces an understandable baseline while preserving the context needed to interpret each retrieved section.

A site profile may tell the generic processing pipeline which HTML components to preserve and which headings to exclude. The pipeline itself remains source-neutral.

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

It supports semantic similarity searches and metadata filtering. It does not perform keyword search or reranking.

The vector database is a derived index rather than the source of truth. Its contents can be recreated from the original content source by running the indexing pipeline again.

### Lexical index

Keyword search uses BM25 over the saved chunk files produced during indexing, not the vector database.

Those files are a second derived index. They must stay in sync with the chunks stored in the vector database so semantic and lexical retrieval operate over the same content.

Lexical retrieval sits behind an internal abstraction, just as vector storage does.

### Retrieval service

The retrieval service contains the shared logic used by both public capability endpoints.

It is responsible for:

- Validating the query and supported filters
- Generating the query embedding
- Searching the vector database
- Searching the saved chunk files with BM25
- Applying metadata filters
- Removing duplicate candidates
- Combining semantic and lexical rankings with reciprocal rank fusion
- Reranking the fused candidates
- Applying a query-level support gate
- Returning the most relevant chunks, or no results when the corpus does not support the query

Both `/v1/search` and `/v1/answer` use this same retrieval service. The application does not maintain separate retrieval implementations for search and answer generation.

Reranking uses an internal provider abstraction. Hybrid fusion happens in the retrieval service, not inside the vector database.

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

The Python service exposes two public capability endpoints and one operational endpoint:

| Endpoint | Responsibility |
|---|---|
| `POST /v1/search` | Retrieve relevant document chunks without generating an answer. |
| `POST /v1/answer` | Retrieve relevant chunks and generate a grounded, cited answer. |
| `GET /health` | Confirm that the service process is running. |

The API is intentionally limited to the system's two user-facing capabilities. `/health` is an operational liveness check, not a third RAG capability. It does not retrieve content, generate answers, or inspect dependencies.

Search and Answer require a shared API key in the `X-API-Key` header. The key authenticates a trusted client application, not an individual end user. `/health` remains unauthenticated so hosting and monitoring systems can check process liveness without storing a secret.

Indexing, connector execution, and other administrative operations remain internal. They may be run through a command-line interface, scheduled process, or protected administrative workflow rather than exposed as public endpoints.

This keeps the public API easier to secure, version, test, document, and maintain.

### WordPress client

The WordPress client provides the first user interface for the service.

It is responsible for:

- Accepting a visitor's query
- Choosing the search or answer experience
- Proxying browser requests through WordPress server-side code
- Adding the API key when forwarding requests to the Python service
- Handling loading, empty, insufficient-evidence, and error states
- Displaying retrieved sections or generated answers
- Rendering trusted source links and citations

The client does not generate embeddings, search the vector database, or call the language model directly.

Browser requests terminate at WordPress. The WordPress server forwards Search and Answer requests to the Python API so the API key is never included in browser JavaScript.

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
2. The connector maps each record into the canonical document model using standard WordPress fields.
3. The selected site profile applies any site-specific metadata, relationships, or processing hints.
4. The content processing pipeline cleans and normalizes the document.
5. The chunking component divides the document into heading-aware sections.
6. The embedding provider generates an embedding for each chunk.
7. The service stores the chunk, embedding, and associated metadata in the vector database.
8. The service writes the same chunks to saved chunk files for BM25 retrieval.
9. When source content changes, the service replaces the affected document's existing chunks in both indexes.
10. When content is deleted or unpublished, the service removes its chunks from both indexes.

### Search data flow

For a search request:

1. The browser sends a query to the WordPress client.
2. WordPress forwards the request to `POST /v1/search` with the API key.
3. The API authenticates the request and validates the query.
4. The retrieval service embeds the query and searches the vector database.
5. The retrieval service searches the saved chunk files with BM25.
6. The service fuses the two ranked lists, reranks the candidates, and applies the support gate.
7. The API formats the selected chunks as search results, or returns an empty result set when the query is unsupported.
8. The WordPress client displays the titles, headings, excerpts, and trusted source links.

No language model is involved in this workflow.

### Answer data flow

For an answer request:

1. The browser sends a query to the WordPress client.
2. WordPress forwards the request to `POST /v1/answer` with the API key.
3. The API authenticates the request and validates the query.
4. The shared retrieval service finds the most relevant chunks, or returns no results when the query is unsupported.
5. The answer generation service assembles the selected chunks into a structured context.
6. The service sends the context and instructions to the language model.
7. The model returns a proposed answer and source identifiers.
8. The citation validation layer checks the proposed citations against the retrieved chunks.
9. The API returns the grounded answer, validated source information, and evidence-sufficiency status.
10. The WordPress client displays the answer and linked sources.

## Architectural boundaries

The architecture maintains the following boundaries:

- Source connectors translate platform-specific content but do not contain RAG logic.
- WordPress site profiles interpret one installation's conventions without modifying the generic connector or the RAG pipeline.
- The canonical document model separates source ingestion from downstream processing.
- Content processing is independent of the source connector.
- Retrieval logic is shared by both public capability endpoints.
- Semantic search, keyword search, and reranking remain separate replaceable stages.
- Answer generation builds on retrieval rather than implementing a separate search path.
- Citation metadata is controlled by the application rather than the language model.
- The WordPress client handles presentation but not retrieval or generation.
- The API key authenticates trusted server-side clients, not end users.
- `/health` is operational and unauthenticated; Search and Answer are capability endpoints.
- The vector database and saved chunk files are rebuildable indexes, not the authoritative content store.

These boundaries are intended to make the system understandable, testable, and extensible without adding unnecessary complexity.

## Deployment view

At a high level, the deployment contains three separately managed systems:

1. The existing WordPress site, which hosts the source content and user interface.
2. The Python RAG service, which exposes the public API and runs the indexing and query pipelines.
3. The vector database, which stores retrieval-ready chunks and embeddings.

The Python service also keeps saved chunk files for BM25 retrieval and communicates with external embedding, reranking, and language-model providers unless local models are selected.

Trusted clients, including the WordPress server-side proxy, authenticate to Search and Answer with a shared API key. Hosting and monitoring systems can call `/health` without that key.

The exact hosting platform, vector database, embedding model, reranking model, and language model are implementation choices documented separately. The architecture should not require a particular vendor for any of these services.
