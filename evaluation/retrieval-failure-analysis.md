# Retrieval Failure Analysis

## Baseline

This analysis describes the initial retrieval baseline for the `doc-landscape-baseline` evaluation dataset.

The baseline uses:

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

- **Primary hit rate@5:** The percentage of answerable cases where at least one primary, answer-bearing source appeared in the top five results.
- **Mean precision@5:** The average percentage of the top five results that were relevant.
- **Precision-evaluable answerable cases: The number of answerable cases with enough retrieved results to calculate precision, out of all answerable cases.
- **Mean recall@5:** The average percentage of the expected relevant sources that appeared in the top five results.
- **Mean reciprocal rank:** A ranking score that gives more credit when the first relevant result appears near the top.
- **Unanswerable accuracy:** The percentage of unanswerable cases where retrieval correctly returned no qualifying results.
- **Overall success rate:** The percentage of all evaluation cases that met their defined success criteria. 

Fifteen of the 17 cases met their current success criteria. The two failures expose different limitations and should be treated separately.

## Failure 1: Multi-section retrieval does not provide complete coverage

**Case:** `multi-section-001`

**Query:**

> How can lost context during chunking, weak source authority, and missing metadata each cause retrieval failures?

**Observed result:**

- Primary hit@5: `false`
- Primary retrieved count: `0`
- Recall@5: `0.250`
- Reciprocal rank: `0.000`
- One relevant result was returned

The retrieved result was the introductory chunk from *When and Why AI Retrieval Fails*. That chunk mentions several of the concepts in the question, including lost context, source authority, and metadata. However, the purpose-built gold set requires the more specific sections that explain each failure mechanism.

### Failure type

**Coverage failure for a compound query.**

The retrieval system found a semantically relevant overview, but it did not retrieve the separate answer-bearing sections needed to cover all parts of the question.

The `1.000` precision score for this case does not indicate successful retrieval. Only one result cleared the retrieval threshold, and that result was relevant. Precision therefore remained high while recall and primary-source coverage were poor.

This illustrates why precision alone is insufficient for evaluating multi-section questions.

### Likely cause

The current retrieval pipeline embeds the complete question as one query and performs one vector similarity search.

A compound question containing several related subtopics can therefore be represented as one blended semantic signal. A broad overview covering all three concepts may be more similar to that combined signal than any of the narrower sections that explain one concept in depth.

This baseline does not establish which retrieval enhancement will solve the problem. It establishes the behavior that future retrieval experiments need to improve.

### Future experiments

Potential experiments include:

- Query decomposition
- Retrieving candidates separately for individual parts of a compound question
- Increasing the candidate pool before final selection
- Hybrid retrieval
- Reranking
- Result-diversity or coverage-aware selection

These are improvement hypotheses, not changes to make during the baseline evaluation.

---

## Failure 2: Semantically adjacent content passes the retrieval threshold for an unsupported question

**Case:** `unanswerable-developer-transition-001`

**Query:**

> How do I transition from technical writer to software developer

**Expected behavior:**

No qualifying results.

**Observed behavior:**

Retrieval returned five chunks above the `0.50` threshold. The highest-scoring result was from *Documentation Engineering* at approximately `0.55`, followed by other content about technical-writing careers, documentation work, engineering workflows, and the SDLC.

None of those sources actually answers how to transition into software development.

### Failure type

**False-positive retrieval for an unsupported but semantically adjacent query.**

This case differs from the Kubernetes and cooking unanswerable cases. Those questions are far outside the indexed site's subject area and correctly return no results. The developer-transition question contains concepts that are strongly represented in the collection:

- technical writers
- careers
- engineering
- development
- technical skills

The embeddings therefore identify genuine semantic similarity even though the retrieved content does not provide the answer the user requested.

### Likely cause

The current minimum-score filter determines whether a chunk is sufficiently similar to return, but semantic similarity is not the same as answerability.

A chunk can be meaningfully related to a query without containing enough evidence to answer it.

This means the retrieval threshold alone cannot be treated as the system's complete unsupported-question detector.

### Future experiments

Potential retrieval-side experiments include:

- Relevance-score calibration
- Stronger handling of borderline results
- Query-to-document intent matching
- Reranking
- Additional answerability signals

However, this case is also important for answer evaluation. The answer-generation layer has its own evidence-sufficiency detection. Even when retrieval returns related chunks, the generator should still decline to answer if those chunks do not support the requested conclusion.

The retrieval failure should therefore remain in the baseline rather than being hidden before answer evaluation.

---

## Successful cases that still reveal retrieval weaknesses

Not every useful finding is a failed case.

### Synonym retrieval works, but the result set is noisy

`synonym-001` passes and retrieves a primary source at rank 1, demonstrating that semantic retrieval can connect differently worded expressions of the same concept.

However:

- Precision@5 is `0.400`.
- Recall@5 is `0.667`.
- Three of the five evaluated results are nonrelevant.

The core semantic behavior works, but result quality drops beyond the strongest matches. This is a useful future benchmark for experiments involving ranking or candidate selection.

### Metadata retrieval succeeds, but the strongest answer-bearing result is not ranked first

`metadata-001` passes, but its reciprocal rank is `0.500`, meaning the first primary answer-bearing source appears at rank 2. Recall@5 is `0.750`.

The rank-1 result is a relevant summary chunk, while a more directly explanatory metadata section appears below it.

This is primarily a ranking-quality issue rather than a retrieval failure.

### Confusable content can outrank more task-specific content

The CMS-selection case succeeds in retrieving the relevant selection article, but a general CMS glossary result ranks above the more directly useful article.

This indicates that semantic similarity alone does not always express which source is most useful for the user's task. Source type, intent, specificity, and authority may eventually be useful ranking signals.

### Updated content is retrievable

`updated-content-001` passes with its primary source at rank 1 and recall@5 of `1.000`.

This provides evidence that updated source content can propagate through indexing and become retrievable in the live vector index. The case should remain in the dataset as a regression check for incremental indexing.

---

## Baseline conclusions

The initial semantic-retrieval implementation performs well on direct, concept-focused questions. It also demonstrates the intended benefit of embeddings by retrieving semantically related content when query wording differs from source wording.

The baseline exposes three broader limitations:

1. **Semantic relevance does not guarantee complete coverage.** Compound questions can retrieve a broad overview while missing the individual sections required for a complete answer.

2. **Semantic relevance does not guarantee answerability.** Related content can exceed the similarity threshold even when the indexed documentation does not actually answer the user's question.

3. **Relevant does not necessarily mean best-ranked.** General or summary content can outrank more specific, task-oriented sources.

These limitations are useful baseline findings rather than reasons to tune the system immediately. Changing retrieval before answer evaluation would remove the ability to observe how the generation layer behaves when retrieval is imperfect.

The next evaluation stage should therefore run answer generation against this unchanged retrieval baseline.

## Handoff to answer evaluation

Two retrieval cases are particularly important for diagnosing the generation layer:

- `multi-section-001` tests whether the generator correctly handles context that is relevant but incomplete. It should not fabricate the missing explanations.
- `unanswerable-developer-transition-001` tests whether evidence-sufficiency detection can reject an unsupported question even though retrieval returned semantically related chunks.

Answer evaluation should distinguish generation failures from retrieval failures. A weak final answer caused by missing evidence should not automatically be attributed to the language model, and a good refusal can demonstrate correct generation behavior even when retrieval itself returned false-positive results.