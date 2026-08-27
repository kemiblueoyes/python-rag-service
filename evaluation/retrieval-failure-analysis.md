# Retrieval Failure Analysis

## Purpose

This report documents the retrieval failures discovered during Phase 10, the experiments used to investigate them, and the current retrieval decision.

The evaluation started with a semantic-search baseline and then tested BM25, hybrid retrieval, Voyage reranking, and an explicit support gate for unsupported questions.

The current evaluation dataset is `doc-landscape-baseline` version `1.3`.

## Initial semantic baseline

The initial baseline used:

- 17 evaluation cases
- 14 answerable cases
- 3 unanswerable cases
- `voyage-4-lite` embeddings
- Vector similarity retrieval
- A minimum retrieval score of `0.50`
- An evaluation depth of 5 results per query

Baseline results:

| Metric | Result |
| --- | ---: |
| Primary hit rate@5 | 92.9% |
| Mean precision@5 | 91.7% |
| Precision-evaluable answerable cases | 12/14 |
| Mean recall@5 | 90.5% |
| Mean reciprocal rank | 0.821 |
| Unanswerable accuracy | 66.7% |
| Overall success rate | 88.2% |

Fifteen of the 17 cases met their original success criteria. Two failures exposed different retrieval problems:

1. `multi-section-001` exposed incomplete coverage for a compound query.
2. `unanswerable-developer-transition-001` exposed false-positive retrieval for an unsupported but semantically adjacent query.

These failures were investigated separately because they require different kinds of fixes.

---

## Failure 1: Multi-section retrieval does not provide complete coverage

**Case:** `multi-section-001`

**Query:**

> How can lost context during chunking, weak source authority, and missing metadata each cause retrieval failures?

### Initial semantic-baseline behavior

The semantic baseline retrieved a relevant overview but did not retrieve the separate answer-bearing sections required to cover all parts of the query.

Initial metrics included:

- Primary hit@5: `false`
- Primary retrieved count: `0`
- Recall@5: `0.250`
- Reciprocal rank: `0.000`

The retrieved overview mentioned several concepts in the question, but the purpose-built gold set requires the specific sections that explain each failure mechanism.

### Failure type

**Coverage failure for a compound query.**

The system can recognize the overall topic while still failing to retrieve enough distinct evidence to answer every part of a compound question.

This is not an answerability problem. The corpus does contain the requested information.

### Hybrid + reranking result

Hybrid retrieval and reranking improved this case substantially, but did not fully solve it.

The final experimental pipeline retrieved five relevant results:

- Precision@5: `1.000`
- Recall@5: `0.714`
- Primary hit@5: `true`
- Primary retrieved count: `1`
- Reciprocal rank: `0.200`
- Top rerank score: `0.812500`

The case still fails because the evaluation requires coverage across multiple specific primary sections, not merely one primary source plus related supporting chunks.

The support gate correctly **accepts** this query because the corpus does support it. The remaining failure is therefore specifically a coverage and selection problem.

### Current interpretation

Hybrid retrieval and reranking improve the candidate set, but a ranking system optimized mainly for individual relevance can still favor broad or overlapping chunks instead of maximizing coverage across separate subtopics.

Potential future approaches include:

- Query decomposition
- Retrieving candidates separately for each part of a compound query
- Coverage-aware or diversity-aware result selection
- Increasing the final result depth for compound questions

No additional coverage mechanism has been selected yet.

---

## Failure 2: Semantically adjacent content is retrieved for an unsupported question

**Case:** `unanswerable-developer-transition-001`

**Query:**

> How do I transition from technical writer to software developer

**Expected behavior:**

No qualifying results.

### Initial semantic-baseline behavior

The semantic baseline returned documentation-career content above the `0.50` vector-similarity threshold even though none of the indexed sources answered the question.

The retrieved chunks were genuinely related to concepts in the query, including technical writing, engineering, development, careers, and technical skills. That made the failure more difficult than the original Kubernetes and cooking expected-empty cases, which were far outside the corpus domain.

### Failure type

**False-positive retrieval for an unsupported but semantically adjacent query.**

The important distinction is:

> Semantic similarity is not the same as answerability.

A chunk can be meaningfully related to a query without containing the evidence needed to answer it.

### Why the original similarity threshold was insufficient

Vector similarity scores for supported and unsupported queries overlapped. Increasing the global vector threshold enough to remove the developer-transition results would also risk removing valid answerable results.

A global semantic-similarity cutoff was therefore not a safe support gate.

---

## Expected-empty experiments

### Standalone BM25

BM25 was tested as a lexical relevance signal over the full indexed corpus.

Standalone BM25 did not solve the expected-empty problem. The developer-transition query received a strong lexical score because the corpus contains overlapping terms such as *technical writer*, *software*, *developer*, and *transition*.

The experiment also showed that BM25 is weaker than semantic retrieval when used alone for meaning-based cases such as `synonym-001`.

The conclusion was not that BM25 is unsuitable for the project. It was that **BM25 alone is not a safe answerability gate**.

### Hybrid semantic + BM25 retrieval

The next experiment combined semantic and BM25 retrieval using Reciprocal Rank Fusion (RRF).

The experimental pipeline used:

1. Top 20 semantic candidates
2. Top 20 BM25 candidates
3. RRF fusion with `k=60`
4. Top 5 fused results for evaluation

RRF combines ranks instead of directly adding vector and BM25 scores, whose numeric scales are not comparable.

Hybrid retrieval improved answerable-case retrieval and restored cases that standalone BM25 struggled with, including synonym retrieval. However, RRF scores still did not provide a safe answerability boundary.

This established an important distinction:

- Hybrid retrieval improved **candidate retrieval**.
- It did not, by itself, solve **support detection**.

### Hybrid retrieval + Voyage reranking

The next experiment added Voyage `rerank-2.5` after hybrid fusion.

The pipeline became:

```text
Query
  ├─> Semantic retrieval: top 20 ─┐
  │                               ├─> RRF fusion
  └─> BM25 retrieval: top 20 ─────┘
                                  ↓
                         top 20 fused candidates
                                  ↓
                         Voyage rerank-2.5
                                  ↓
                               top 5
```

This produced the first useful separation between supported and unsupported queries.

---

## Expanded expected-empty evaluation

Because the original dataset contained only three expected-empty cases, five additional in-domain but unsupported cases were added.

The dataset increased from 17 to 22 cases:

- 14 answerable
- 8 expected-empty

The added cases intentionally use concepts that are strongly represented in the corpus while asking for information the corpus does not provide:

- `unanswerable-hybrid-implementation-001`
- `unanswerable-vector-db-selection-001`
- `unanswerable-embedding-finetuning-001`
- `unanswerable-cms-migration-001`
- `unanswerable-doc-engineering-certification-001`

These are more useful support-gate tests than only using obviously out-of-domain questions.

### Top rerank scores for expected-empty cases

| Case | Top rerank score |
| --- | ---: |
| `unanswerable-cooking-001` | 0.277344 |
| `unanswerable-kubernetes-001` | 0.328125 |
| `unanswerable-cms-migration-001` | 0.390625 |
| `unanswerable-vector-db-selection-001` | 0.421875 |
| `unanswerable-doc-engineering-certification-001` | 0.503906 |
| `unanswerable-hybrid-implementation-001` | 0.578125 |
| `unanswerable-embedding-finetuning-001` | 0.597656 |
| `unanswerable-developer-transition-001` | 0.640625 |

The highest unsupported score is `0.640625`.

The lowest top rerank score among answerable cases is `0.812500`, from `multi-section-001`.

The current dataset therefore shows a clear separation between unsupported and supported queries.

---

## Provisional support gate

A provisional query-level support cutoff of `0.70` was evaluated.

The rule is:

```text
if top rerank score < 0.70:
    return no qualifying results
else:
    keep the reranked result set
```

The cutoff is applied at the **query level**, not separately to each chunk.

For example, an accepted query may contain lower-ranked chunks with rerank scores below `0.70`. Those chunks are not individually removed merely because they fall below the query-level support threshold.

### Support-gate results

| Metric | Result |
| --- | ---: |
| Total cases | 22 |
| Correct gate decisions | 22/22 |
| Overall gate accuracy | 100.0% |
| Answerable queries accepted | 14/14 |
| Answerable acceptance rate | 100.0% |
| Expected-empty queries rejected | 8/8 |
| Expected-empty rejection rate | 100.0% |
| False positives | 0 |
| False negatives | 0 |

The `0.70` cutoff therefore correctly separates all supported and unsupported queries in the current evaluation dataset.

The cutoff remains **provisional**, not universal. It must be treated as model-, corpus-, and pipeline-specific and revalidated when those conditions change.

---

## Final hybrid + reranking retrieval results

The final experimental pipeline uses:

- `voyage-4-lite` embeddings
- Semantic candidate depth: 20
- BM25 candidate depth: 20
- RRF fusion with `k=60`
- 20 fused candidates sent to `rerank-2.5`
- Evaluation depth: 5
- Query-level support cutoff: `0.70`

Answerable-case retrieval results:

| Metric | Result |
| --- | ---: |
| Answerable cases | 14 |
| Successful answerable cases | 13 |
| Answerable success rate | 92.9% |
| Primary hit rate@5 | 100.0% |
| Mean precision@5 | 94.3% |
| Precision-evaluable answerable cases | 14/14 |
| Mean recall@5 | 76.5% |
| Mean reciprocal rank | 0.907 |

The single remaining answerable-case failure is `multi-section-001`.

This is compatible with the support-gate result: the gate correctly determines that the corpus supports the query, while the retrieval benchmark correctly identifies that the top-five result set does not provide the required primary-source coverage.

---

## Other useful findings

### Synonym retrieval remains strong

`synonym-001` is a useful regression case because BM25 alone struggled with it.

Under hybrid retrieval plus reranking:

- Primary hit@5: `true`
- Precision@5: `1.000`
- Recall@5: `0.833`
- Reciprocal rank: `1.000`
- All five evaluated results are relevant

This shows why the lexical component should complement rather than replace semantic retrieval.

### Ranking improves, but relevance is not identical to usefulness

Cases such as CMS selection and documentation engineering continue to show that several chunks can be relevant while differing in specificity or usefulness.

Reranking improves ordering, but future source-authority, specificity, or task-intent signals may still improve which relevant result appears first.

### Updated content remains retrievable

`updated-content-001` continues to pass and retrieves current revised documentation successfully.

It remains useful as a regression check that updated source content propagates through indexing and remains retrievable after retrieval-pipeline changes.

---

## Current conclusions

The Phase 10 experiments support the following conclusions:

1. **Vector similarity alone is not a reliable support gate.** Semantically adjacent content can score highly even when it does not answer the query.

2. **BM25 alone is not a reliable support gate.** Lexical overlap can also be strong for unsupported questions, and BM25 alone loses meaning-based retrieval quality.

3. **Hybrid semantic + BM25 retrieval improves the candidate pool.** RRF combines complementary semantic and lexical signals without requiring their raw scores to share a scale.

4. **Reranking is the stage that produced useful support separation.** Voyage reranking over the hybrid candidate pool separated the tested answerable and expected-empty queries.

5. **A `0.70` top-rerank-score gate is a viable provisional support rule for the current corpus and models.** It achieved 100% gate accuracy across the current 22-case dataset.

6. **Support detection and retrieval coverage are separate problems.** `multi-section-001` correctly passes the support gate while still failing the retrieval-coverage requirement.

7. **An LLM support grader is not currently required.** The hybrid + reranking pipeline provides a non-generative support signal that succeeds on the current evaluation set. An LLM grader can remain a future fallback if the score separation stops holding as the corpus or query distribution changes.

---

## Current decision

The current retrieval candidate for production is:

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

This decision is based on the current evaluation dataset rather than on the assumption that any one retrieval score is universally meaningful.

The `0.70` threshold should remain configurable and should be regression-tested whenever the corpus, embedding model, reranking model, chunking strategy, or retrieval configuration changes.

The production `RetrievalService` should not be considered updated until this experimental pipeline is deliberately integrated and covered by service/API tests.

---

## Remaining retrieval limitation

`multi-section-001` remains the only known answerable-case failure in the final experiment.

It should be tracked separately from the expected-empty problem. The current pipeline can determine that the query is supported, but it does not yet guarantee that a top-five result set covers every distinct subtopic required by a compound query.

This limitation can either be investigated further during Phase 10 or documented as a known retrieval limitation before moving fully into answer evaluation. In either case, answer evaluation should continue to verify that generation does not invent missing details when retrieved context is incomplete.
