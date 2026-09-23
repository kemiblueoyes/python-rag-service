---
version: 1
---

# Terminology

## System, source, and content model

| Concept | Preferred term | Rule |
| :---- | :---- | :---- |
| The project/product | **Python RAG Service** | Use the full name on first mention or when referring to the project as a whole. |
| Shortened product reference | **RAG service** | Preferred shortened form after the full name has been established. |
| Generic shortened reference | **service** | Fine when the subject is unambiguous. |
| Core application | **Python RAG service** | Use when distinguishing the Python application from WordPress, Qdrant, or external providers. Avoid casually switching to *backend*, *RAG engine*, or *AI engine*. |
| External system supplying content | **content source** | Generic term for WordPress or future systems whose content is indexed. |
| Code that reads a content source | **connector** | A connector retrieves source-specific content and maps it into the canonical document model. Distinct from **client** and not to be used interchangeably. |
| WordPress ingestion component | **WordPress connector** | Do not call this the WordPress client or use *WordPress integration* when specifically referring to ingestion. |
| Application consuming the API | **client** | A system that sends requests to the RAG API and uses its responses. Distinct from **connector** and not to be used interchangeably. |
| Current WordPress consumer | **WordPress client** | Keep distinct from the WordPress connector. |
| Platform-neutral document representation | **canonical document** | Preferred term. Avoid *normalized document* as a synonym because normalization is a later processing step. |
| Original authoritative content | **source content** | The content held by WordPress or another authoritative content system. |
| Authoritative system | **source of truth** | Use for the system that owns the original content. The vector database is not the source of truth. |
| Smaller retrievable unit | **chunk** | Standard term for a section produced during chunking. |
| Unique chunk identifier | **chunk ID** | Use when discussing the identifier itself. |
| Searchable derived data | **index** | The collection of retrieval-ready data produced from source content. Should not be used interchangeably with **vector database**. They are not synonyms.  |
| Process of building/updating that data | **indexing** | Covers processing content and adding it to the retrieval system. |
| Database holding vectors and metadata | **vector database** | Use consistently for Qdrant in architecture-level prose. I would avoid switching freely between *vector store* and *vector database*. |

The project uses **source** in several senses:

* WordPress is a **content source**.  
* A retrieved chunk may become an answer **source**.  
* The canonical model has a `source` field.  
* Citations point readers to **sources**.

Qualify **source** when ambiguity is possible:

* **content source** — WordPress, future CMS, Git repository, etc.  
* **source content** — the actual original documentation, such as a blog post from WordPress.  
* **retrieved source** — define and use this term only if the documentation actually needs a separate label for a source selected by retrieval.  
* **source link** — URL shown with a citation.  
* **source metadata** — title, URL, heading, ID, etc. preserved from the canonical source.

Then a standalone **source** is fine when the context clearly establishes which meaning we mean.

## Retrieval

| Concept | Preferred term | Rule |
| :---- | :---- | :---- |
| Overall process of finding relevant content | **retrieval** | Use for the system process that finds candidate chunks for a query. |
| User-facing capability | **search** | Use for the `/v1/search` experience and API behavior exposed to users. |
| Embedding-based retrieval used by the service | **vector retrieval** | Use when specifically referring to the step that compares query embeddings with chunk embeddings to find similar chunks. **Vector retrieval** is one part of the project’s hybrid retrieval pipeline; it is not the whole retrieval process. |
| Meaning-based search as a general concept | **semantic search** | Use when explaining the general idea of finding content based on meaning rather than exact words. Do not use **semantic search** as the name for this project’s full retrieval pipeline, because the pipeline also uses BM25, fusion, and reranking. |
| Keyword-based retrieval | **lexical retrieval** | Preferred general term for term-matching retrieval. |
| Current lexical method | **BM25 retrieval** | Use when specifically referring to the implemented BM25 method. |
| Combined lexical \+ vector retrieval inside the RAG service | **hybrid retrieval** | Preferred project term for the implemented internal retrieval approach. |
| General search pattern that combines multiple retrieval methods | **hybrid search** | Use when discussing the broader search concept, industry terminology, or systems in general. Do not use it as the default name for this project’s internal retrieval pipeline. |
| Chunks being considered during retrieval | **candidate chunks** | Use for chunks returned by the initial retrieval methods before the pipeline finishes selecting the best ones. Candidate chunks are not yet **retrieved chunks** or **search results**. |
| Chunks selected by the retrieval pipeline | **retrieved chunks** | Use for chunks that remain after fusion, reranking, and other retrieval steps have selected the content to return or use as evidence. They are no longer just **candidate chunks**. For `/v1/search`, these become **search results**. |
| Results returned by the Search API | **search results** | Use for the final results returned by `/v1/search`. Search results come from the selected **retrieved chunks**. Do not use this term for intermediate **candidate chunks**. |
| Combining ranked result sets | **reciprocal rank fusion (RRF)** | Spell out on first mention; use **RRF** afterward. |
| Ordering candidates by relevance | **ranking** | General term. |
| Second-stage relevance ordering | **reranking** | Preferred spelling. Do not use *re-ranking*. |
| Model/service that performs reranking | **reranker** | Use for the component or model. |
| How closely a chunk relates to a query | **relevance** | Use for how closely retrieved content relates to the query. Do not use **relevance** to imply that the content contains enough information to answer the query. Use **support** instead. |
| Whether retrieved evidence can answer the user’s question | **support** | Use for whether the retrieved content contains enough information to answer the user’s question. A chunk can be **relevant** to the topic without actually answering the question. |
| Decision about whether any retrieved content adequately supports the query | **support gate** | Use for the explicit post-retrieval decision point, assuming this remains the implemented name. Don’t use “threshold” and “gate” interchangeably. A threshold may be one input to a gate, but the two are not synonyms. |
| Query that the corpus cannot adequately answer | **unsupported query** | Preferred term when the documentation does not contain enough relevant evidence. |
| Search response with no acceptable matches | **no relevant results** | Use for `/v1/search` when the support/relevance gate rejects all candidates. |

Casual use of the following is discouraged:

**AI search**, **smart search**, **semantic retrieval pipeline** as a name for the whole pipeline, **hybrid search** in project-specific architecture prose, **re-ranking**, and using **result** for every intermediate candidate.

## Answer-generation and citation

| Concept | Preferred term | Rule |
| :---- | :---- | :---- |
| Answer produced from retrieved documentation | **grounded answer** | Use for an answer generated from the retrieved evidence, a grounded answer should be supported by the retrieved content and include validated sources when applicable. Not the same as the **generated answer**. |
| Any answer produced by the language model | **generated answer** | Use when referring to the model output before or regardless of whether grounding has been established. Do not use **generated answer** and **grounded answer** as synonyms. |
| Retrieved content supplied to the model | **context** | Use for the selected retrieved chunks that are assembled and sent to the language model. **Context** is what the model receives; **evidence** is the information in that context that supports an answer. |
| Information that supports an answer | **evidence** | Use for retrieved information that supports the answer to the user’s question. Do not use **context** and **evidence** interchangeably: context may contain information that does not end up supporting the answer. |
| Enough evidence to answer the question | **sufficient evidence** | Use when the retrieved evidence contains enough information to generate a grounded answer. Contrast with **insufficient evidence**. |
| Not enough evidence to answer the question | **insufficient evidence** | Use when the retrieved content does not contain enough information to support a grounded answer. This is different from **no relevant results**: relevant content may have been retrieved but still not contain enough information to answer the question. |
| Documentation used to support an answer | **source** | Use for the documentation page or section that provides evidence for the answer. Do not confuse this with a **content source**, such as WordPress, which is the system the documentation comes from. |
| Reference connecting an answer to a source | **citation** | Use for the reference that connects part of a generated answer to a trusted retrieved source. A citation is not itself the source; it points to one. |
| Application check of model-proposed citations | **citation validation** | Use for the application-side process that verifies that cited chunks were actually retrieved and that their IDs, titles, headings, and URLs come from trusted metadata. Do not say the model **validates** or **verifies** its own citations. |
| Statement not supported by the provided evidence | **unsupported claim** | Use when a generated statement is not supported by the retrieved evidence. This describes the output, not the user’s query. Do not confuse **unsupported claim** with **unsupported query**. |
| Model-generated information that is false or unsupported | **hallucination** | Use sparingly and only when discussing the general AI failure mode. In project-specific evaluation and error analysis, prefer the more precise term **unsupported claim** when that is what actually occurred. |

## Evaluation and quality terms

| Concept | Preferred term | Rule |
| :---- | :---- | :---- |
| Systematic measurement of system quality | **evaluation** | Use for the overall process of measuring retrieval or answer quality against defined expectations. Do not use **testing** as a synonym when you specifically mean quality evaluation. |
| Maintained collection of evaluation cases | **evaluation dataset** | Use for the complete set of cases used to evaluate retrieval or answer quality. Do not use **test case** when referring to the dataset as a whole. |
| One item in an evaluation dataset | **test case** | Use for one query and its expected behavior or results within an evaluation dataset. |
| Behavior or result a test case should produce | **expected result** | Use for the outcome defined for a test case. This may include expected relevant chunks, expected answer behavior, or an expected empty result. |
| Retrieved content that should help answer the query | **relevant** | Use for a chunk or result judged to be useful for the query. Contrast with **nonrelevant**. Do not use **relevant** to mean that the chunk alone contains enough information to support an answer; **relevant** and **support** are not synonyms. |
| Retrieved content that should not help answer the query | **nonrelevant** | Use for a chunk or result judged not useful for the query. Use **nonrelevant** consistently rather than alternating with *irrelevant* in evaluation labels. |
| Test case where retrieval should return no acceptable results | **expected-empty** | Use for an evaluation case where the correct retrieval behavior is to return no relevant results. This describes the expected outcome of the test case, not a general **unsupported query** condition. |
| Measurement of whether retrieval finds the right content | **retrieval evaluation** | Use for evaluation of retrieved chunks, their relevance, and their rank. Keep separate from **answer evaluation** so retrieval failures can be distinguished from generation failures. |
| Measurement of whether generated answers are supported and correct | **answer evaluation** | Use for evaluation of generated answers, including evidence support, citations, omissions, and insufficient-evidence behavior. Keep separate from **retrieval evaluation**. |
| Share of returned results that are relevant | **precision** | Use for the proportion of retrieved results judged relevant. Include the cutoff when needed, such as **Precision@5**. |
| Share of expected relevant results that were retrieved | **recall** | Use for how much of the known relevant content the retrieval system found. Include the cutoff when needed, such as **Recall@5**. |
| Measure based on the rank of the first relevant result | **reciprocal rank** | Use for the reciprocal of the position of the first relevant result. Use the exact metric name used by the evaluation output; don’t shorten it to **rank**. |
| Evaluation results used as a comparison point | **baseline** | Use for a documented set of evaluation results that provides a reference point for later changes. Do not automatically use **baseline** to mean the latest results. |
| Latest results for the current implementation | **current evaluation results** | Use for the most recent evaluation results produced by the current implementation. Do not use **baseline** as a synonym unless those current results are intentionally being established as a new baseline. |
| Evaluation case that does not meet its expected result | **failure** | Use when an evaluation test case does not produce the expected result. A failure is not automatically a **regression** or a **known limitation**; those terms require additional context. |
| Known gap or constraint in the current system | **known limitation** | Use for behavior or capability that is currently constrained, incomplete, or known not to work in some situations. Do not use for every failed test; a failure becomes a known limitation only when it represents an understood current constraint. |
| Previously working or acceptable behavior that becomes worse | **regression** | Use when a change causes previously acceptable retrieval or answer behavior to degrade. A newly discovered weakness is not automatically a regression. |
