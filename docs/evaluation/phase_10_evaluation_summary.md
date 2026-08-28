# Phase 10 Evaluation Summary

## Purpose

Phase 10 established an evaluation framework for the Python RAG Service and used it to test retrieval quality, unsupported-query handling, answer structure, citation behavior, and generated-answer quality.

The evaluation deliberately separates **retrieval evaluation** from **answer evaluation**. A retrieval failure does not automatically mean the generated answer is poor, and a good answer does not erase a retrieval weakness.

## Evaluation scope

The final evaluation set contains **22 cases**:

- **14 answerable cases**
- **8 expected-empty cases**, where the corpus does not contain enough information to answer the query

The dataset includes exact-answer, confusable, ambiguous, synonym, multi-section, updated-content, and unanswerable cases.

The retrieval failure analysis was recorded against dataset version `1.3`. The final answer baseline and qualitative review were recorded against dataset version `1.5`.

## Retrieval evaluation

### Final retrieval pipeline

The evaluated retrieval pipeline combines semantic and lexical retrieval:

```text
Semantic retrieval: top 20
        +
BM25 retrieval: top 20
        ↓
RRF fusion (k=60)
        ↓
Top 20 fused candidates
        ↓
Voyage rerank-2.5
        ↓
Top rerank score < 0.70?
        ├─ yes -> no qualifying results
        └─ no  -> return reranked results
```

The `0.70` value is a **query-level support cutoff**. It is provisional and specific to the current corpus, models, and retrieval configuration.

### Retrieval results

For the 14 answerable cases:

| Metric | Result |
| --- | ---: |
| Successful answerable cases | 13/14 |
| Answerable success rate | 92.9% |
| Primary hit rate@5 | 100.0% |
| Mean precision@5 | 94.3% |
| Mean recall@5 | 76.5% |
| Mean reciprocal rank | 0.907 |

For support detection across all 22 cases:

| Metric | Result |
| --- | ---: |
| Correct support-gate decisions | 22/22 |
| Overall gate accuracy | 100.0% |
| Answerable queries accepted | 14/14 |
| Expected-empty queries rejected | 8/8 |
| False positives | 0 |
| False negatives | 0 |

### Known retrieval limitation

`multi-section-001` remains the only known answerable-case retrieval failure.

The query asks about three separate retrieval-failure mechanisms. The system correctly recognizes that the corpus supports the question, but the top-five result set does not satisfy the benchmark's required coverage across the designated primary sections.

This is a **coverage problem**, not a support-detection problem.

Possible future approaches include query decomposition, per-subtopic retrieval, coverage-aware or diversity-aware selection, or a larger result depth for compound questions.

## Answer structural evaluation

The final answer baseline used dataset version `1.5`, `voyage-4-lite` embeddings, `gpt-5.6-terra` generation, five retrieval results per query, and the `0.70` retrieval support cutoff.

| Metric | Result |
| --- | ---: |
| Total cases | 22 |
| Structural passes | 22/22 |
| Structural pass rate | 100.0% |
| Evidence-sufficiency accuracy | 100.0% |
| Citation-behavior accuracy | 100.0% |
| Answerable-case pass rate | 100.0% |
| Unanswerable-case pass rate | 100.0% |

The structural evaluator checks whether the system correctly identifies sufficient evidence and whether citations follow the expected source rules. It does not judge semantic completeness or writing quality.

## Human qualitative answer evaluation

The 14 answerable cases were reviewed manually on four dimensions:

- **Support / faithfulness** — whether meaningful claims are supported by the retrieved sources
- **Required-point completeness** — whether the answer covers the important points expected for the case
- **Unsupported details** — whether the answer adds claims that are not supported by retrieved evidence
- **Focus / relevance** — whether the answer stays on the user's question instead of drifting into related but unnecessary material

A strict qualitative pass requires a score of `2` on all four dimensions.

| Metric | Result |
| --- | ---: |
| Answerable cases reviewed | 14 |
| Strict passes | 14/14 |
| Strict failures | 0 |
| Strict qualitative pass rate | 100.0% |
| Support / faithfulness average | 2.00 / 2 |
| Required-point completeness average | 2.00 / 2 |
| Unsupported details average | 2.00 / 2 |
| Focus / relevance average | 2.00 / 2 |

### Prompt refinement discovered through evaluation

An earlier answer run exposed one qualitative weakness in `context-001`.

The answer was supported by its cited sources, but it drifted into how AI assistants use context even though the question asked about context in documentation. The prompt was updated to tell the model to answer only what the user asked and ignore related source material that is not needed.

After that change, `context-001` passed all four qualitative dimensions in the final `1.5` run.

## Key findings

1. **Semantic similarity alone cannot determine whether the corpus actually supports a query.** Topically related chunks can still be insufficient.

2. **BM25 alone does not solve support detection either.** Lexical overlap can be strong for unsupported questions, and lexical retrieval alone loses useful meaning-based matches.

3. **Hybrid semantic + BM25 retrieval improves the candidate pool.** The two retrieval methods provide complementary signals.

4. **Reranking produced a useful support signal for the current corpus.** A top rerank score cutoff of `0.70` correctly separated all 14 supported queries from all 8 expected-empty queries in the current evaluation set.

5. **The support cutoff is not universal.** It should be revalidated if the corpus, embedding model, reranking model, chunking strategy, or retrieval configuration changes.

6. **Support detection and retrieval coverage are different problems.** `multi-section-001` passes the support gate but still fails the stricter retrieval-coverage benchmark.

7. **Retrieval quality and answer quality should remain separate evaluations.** `multi-section-001` demonstrates this clearly: retrieval does not satisfy the gold coverage requirement, but the generated answer still covers all three required points and passes the qualitative review.

8. **Human qualitative review catches problems that structural checks cannot.** The earlier `context-001` answer was structurally valid but unnecessarily off-topic. The qualitative rubric exposed that weakness and led to a prompt improvement.

9. **An LLM support grader is not currently required.** The hybrid + reranking support signal handles all expected-empty cases in the current dataset without adding a second LLM call to every production query.

## Phase 10 outcome

Phase 10 now provides:

- a versioned evaluation dataset
- retrieval relevance judgments
- expected-empty cases
- BM25, hybrid retrieval, reranking, and support-gate experiments
- retrieval failure analysis
- deterministic answer evaluation
- human qualitative answer evaluation
- saved JSON and Markdown evaluation artifacts
- regression cases for synonym retrieval, compound queries, updated content, unsupported queries, citation behavior, and answer focus

The remaining known retrieval limitation is `multi-section-001`. It is documented rather than treated as an answer-generation failure.

With that limitation recorded, the Phase 10 evaluation framework and current evaluation pass are complete.
