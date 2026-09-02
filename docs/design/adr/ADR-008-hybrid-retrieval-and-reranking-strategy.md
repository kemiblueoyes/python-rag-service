# ADR-008: Hybrid Retrieval and Reranking Strategy

## Status

Accepted

## Date

2026-09-02

## Context

The RAG service initially used semantic vector search to retrieve document chunks. Semantic retrieval worked well for meaning-based matches, but Phase 10 evaluation exposed two limitations:

- Semantically related content could be returned even when the corpus did not contain enough information to answer the query.
- A compound query could retrieve content about the overall topic without retrieving enough distinct evidence to cover all parts of the question.

The first limitation showed that semantic similarity is not the same as answerability. Vector similarity scores for supported and unsupported queries overlapped, so a single global similarity threshold could reject useful results while still allowing unsupported ones.

BM25 lexical retrieval was evaluated as an additional relevance signal. It improved exact-term matching but did not solve support detection by itself. Unsupported queries could still receive strong lexical scores when their words appeared throughout the corpus, while meaning-based cases such as synonym queries were weaker under standalone BM25.

The retrieval architecture therefore needed to:

- Preserve semantic matching for concepts, paraphrases, and synonyms
- Add lexical matching for exact words and phrases
- Combine results whose original score scales are not directly comparable
- Improve the ordering of the combined candidates
- Return no results when the corpus does not sufficiently support the query
- Keep retrieval shared between the `/v1/search` and `/v1/answer` endpoints
- Keep lexical retrieval, fusion, and reranking replaceable through internal abstractions
- Avoid adding a second LLM call to every query unless evaluation shows that one is necessary

## Decision

Use a hybrid retrieval pipeline that combines semantic vector retrieval and BM25 lexical retrieval, fuses their ranked results with Reciprocal Rank Fusion (RRF), reranks the fused candidates with Voyage, and applies a query-level support gate before returning results.

The default production retrieval path is:

1. Retrieve up to 20 semantic candidates from Qdrant using Voyage `voyage-4-lite` embeddings.
2. Retrieve up to 20 lexical candidates from the indexed chunk corpus using BM25.
3. Remove duplicate chunks within each result set.
4. Combine the semantic and lexical rankings using RRF with `k=60`.
5. Keep the top 20 fused candidates.
6. Rerank the fused candidates with Voyage `rerank-2.5`.
7. Compare the highest rerank score with the configured support cutoff of `0.70`.
8. Return no qualifying results when the highest score is below the cutoff; otherwise, return the requested number of reranked results.

RRF is used because it combines rank positions rather than adding raw semantic and BM25 scores, which use different and non-comparable scales. A chunk that ranks well in both result sets receives more weight than a chunk that ranks well in only one.

The support cutoff is applied to the query as a whole, not to each returned chunk. If the top reranked candidate demonstrates sufficient support, lower-ranked candidates are not individually removed merely because their scores fall below `0.70`.

The `0.70` cutoff was selected through evaluation of the current corpus, models, and pipeline configuration. Across the 22-case evaluation set, it accepted all 14 answerable queries and rejected all 8 expected-empty queries. It is configurable and must not be treated as a universal threshold.

Both public capability endpoints use the same configured `RetrievalService`. Vector storage, lexical retrieval, and reranking remain behind internal interfaces, while fusion and support gating are coordinated by the retrieval service.

## Options Considered

### Semantic retrieval with a global similarity threshold

Considered as the original retrieval approach.

Advantages:

- Simple retrieval path
- Strong meaning-based matching
- Handles paraphrases and synonyms better than lexical retrieval alone
- Requires only the existing embedding provider and vector store

Disadvantages:

- Returns the closest available chunks even when the corpus does not answer the query
- Supported and unsupported queries can have overlapping vector scores
- A stricter global threshold risks rejecting valid results
- Does not benefit from exact-term evidence supplied by lexical retrieval

### Standalone BM25 lexical retrieval

Evaluated.

Advantages:

- Strong exact-word and exact-phrase matching
- Does not require an embedding request
- Provides an interpretable lexical relevance signal

Disadvantages:

- Strong word overlap does not prove that the corpus answers the query
- Weaker for synonyms and other meaning-based matches
- Cannot replace semantic retrieval without losing useful retrieval quality
- BM25 scores did not provide a safe support boundary in evaluation

### Hybrid semantic and BM25 retrieval with RRF only

Evaluated.

Advantages:

- Combines complementary semantic and lexical signals
- Avoids comparing incompatible raw score scales
- Improves the candidate pool and restores meaning-based cases that BM25 alone misses
- Does not add a reranking provider call

Disadvantages:

- RRF scores did not provide a safe boundary between supported and unsupported queries
- Fusion improves candidate retrieval but does not independently determine answerability
- Final ordering is based on the two original rankings rather than deeper query-to-chunk comparison

### Hybrid retrieval with RRF, Voyage reranking, and a support gate

Selected.

Advantages:

- Preserves semantic and lexical retrieval strengths
- Improves final candidate ordering through query-aware reranking
- Produced a useful separation between supported and unsupported queries in the current evaluation set
- Correctly handled all 22 evaluated support-gate cases
- Avoids an additional LLM support-grading call for every production query
- Fits the existing provider-neutral retrieval architecture

Disadvantages:

- Adds latency, cost, and an external reranking dependency to every retrieval request
- Requires maintaining a BM25 corpus alongside the Qdrant vector index
- Makes retrieval configuration and failure handling more complex
- The support cutoff is specific to the evaluated corpus, models, and configuration
- Does not fully solve evidence coverage for compound, multi-section queries

### LLM support grader after retrieval

Considered as a possible support-detection mechanism but not selected for the current pipeline.

Advantages:

- Could judge whether retrieved evidence actually supports a query when numeric score ranges overlap
- Could handle more nuanced support decisions than a fixed score cutoff

Disadvantages:

- Adds another LLM call before answer generation
- Increases latency, cost, and operational complexity
- Introduces nondeterminism into the support decision
- Was not required to separate supported and unsupported cases in the current evaluation set

## Consequences

### Positive

- The service uses complementary semantic and lexical signals instead of relying on either one alone.
- `/v1/search` and `/v1/answer` share the same retrieval behavior.
- RRF combines results without requiring semantic and BM25 scores to share a scale.
- Voyage reranking improves result ordering and supplies the strongest evaluated support signal.
- Unsupported queries can return an empty result set before answer generation.
- The current support gate avoids a separate LLM grading call.
- Retrieval stages remain replaceable through internal interfaces and configuration.
- Evaluation artifacts provide a repeatable baseline for future retrieval changes.

### Negative

- Each retrieval request now performs embedding, vector search, BM25 search, fusion, and external reranking.
- Reranking increases request latency and provider cost.
- The lexical corpus must remain synchronized with the indexed chunks in Qdrant.
- The support cutoff can become unreliable when the corpus, models, chunking strategy, or retrieval settings change.
- A single top score indicates query support but does not guarantee complete evidence coverage.
- The current pipeline still has a known coverage limitation for the `multi-section-001` compound query.

### Future Considerations

Re-evaluate the support cutoff whenever any of the following changes:

- Indexed corpus or its content distribution
- Embedding model
- Reranking model
- Chunking strategy
- Candidate depths
- RRF configuration
- Query patterns or evaluation dataset

Future retrieval improvements may include:

- Query decomposition for compound questions
- Per-subtopic retrieval
- Coverage-aware or diversity-aware result selection
- Adaptive result depth
- Moving lexical retrieval into the vector database
- Additional lexical or reranking provider adapters
- An LLM support grader if supported and unsupported rerank-score ranges begin to overlap

Any change to the retrieval strategy should be evaluated separately for candidate quality, evidence coverage, and query-level support detection before it replaces the current pipeline.
