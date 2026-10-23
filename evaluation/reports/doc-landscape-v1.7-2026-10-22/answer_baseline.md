# Answer Evaluation Baseline

Generated: 2026-10-22T19:39:06.033957+00:00

Dataset: `doc-landscape-baseline`

Dataset version: `1.7`

Collection: `rag_chunks`

Embedding model: `voyage-4-lite`

Generation model: `gpt-5.6-terra`

Retrieval support cutoff: `0.70`

Retrieval results per query: `5`

## Summary

- Total cases: **22**
- Passed structural checks: **22**
- Structural pass rate: **100.0%**
- Evidence-sufficiency accuracy: **100.0%**
- Citation-behavior accuracy: **100.0%**
- Answerable-case pass rate: **100.0%**
- Unanswerable-case pass rate: **100.0%**

> Structural PASS/FAIL does not score whether the generated answer covers the required semantic points. Required points are included below for qualitative review.

## Case results

### terminology-001 — PASS

**Category:** `exact_answer`

**Query:** Why can inconsistent terminology cause AI retrieval to fail?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Inconsistent terminology weakens the signals retrieval uses to connect a query with the right content, increasing the chance that relevant content is missed or ranked less effectively.

#### Generated answer

Inconsistent terminology weakens the language, metadata, taxonomy, and structural signals retrieval uses to connect a query with relevant content. A system may not recognize that multiple labels refer to the same feature, especially when internal and customer-facing terms, acronyms, product names, or aliases differ, so relevant material can be overlooked. [S1][S2]

It also hurts term-matching retrieval: content that does not use the terms users search for may rank poorly or not be found at all—for example, when users search for “payback tracking” but documentation uses “commission reconciliation.” [S3][S4]

#### Cited sources

##### [S1] What Retrieval Systems Need from Your Content

**Heading:** Retrieval Depends on Consistent Signals

**Chunk ID:** `wordpress:page:2368:chunk:v1:ccba4172e13bcc89f3f437d7113db01f0f065827272dd12419d213cd9b0c1b97`

**Retrieval score:** `0.906250`

**Source text:**

Retrieval systems look for patterns.

Some patterns come from language. Others come from metadata, content relationships, taxonomy, or document structure. Together, these signals help the system determine what content should be surfaced for a particular query.

Terminology plays an important role here. If a documentation set refers to the same feature as an AI assistant, support copilot, knowledge assistant, and virtual helper, a human reader can usually infer that the terms are related. Retrieval systems may not always make the same connection.

The same challenge appears when product names change, when teams use internal terminology that differs from customer-facing language, or when multiple groups describe similar concepts differently across the documentation set.

Consistency strengthens retrieval because it strengthens the signals retrieval systems use to identify relationships between pieces of content. Inconsistent terminology weakens those signals and increases the likelihood that relevant information will be overlooked.

##### [S2] How RAG Works in Retrieval-Based AI Systems

**Heading:** Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 4: Embeddings

**Chunk ID:** `wordpress:page:2366:chunk:v1:e608885ce1731409468b9d616ddc59062c0f90a8528615449f0a5d5202fe80e2`

**Retrieval score:** `0.835938`

**Source text:**

Once the content is chunked, the system converts those chunks into embeddings. An embedding is a mathematical representation of related meaning.

The goal isn’t to store language exactly as written. It’s to place conceptually related content near other conceptually related content in a semantic space. This is what allows retrieval systems to move beyond simple keyword matching.

For example, a retrieval system might connect:

- “rotate API credentials”
- “change access token”
- “regenerate authentication keys”

as conceptually related operations even if the wording differs.

That flexibility is very powerful. However, embeddings are not magic understanding. Terminology consistency still matters because if teams use different names for the same concept across documentation systems , retrieval quality can weaken.

The same thing happens when:

- internal terminology differs heavily from customer-facing terminology
- acronyms are inconsistent
- product names change repeatedly
- feature aliases accumulate over time

Embeddings help retrieval systems identify related meaning. They don’t eliminate the need for coherent information architecture.

##### [S3] BM25

**Heading:** Why This Matters for Technical Writers

**Chunk ID:** `wordpress:glossary:2455:chunk:v1:3344c6d3a4216303c5a33e3ec0dcec38578fdc112dd395371636d429a3b30ae8`

**Retrieval score:** `0.761719`

**Source text:**

BM25 is relevant to technical writers documenting AI search and retrieval products, particularly those built on hybrid retrieval architectures that combine keyword and semantic search. Understanding that BM25 operates on term matching helps explain why precise, consistent terminology in documentation affects search outcomes. Content that uses the same terms users are likely to query will perform better under BM25 retrieval than content that paraphrases or avoids specific terms. This is a practical argument for terminology consistency and controlled vocabulary in documentation systems that feed into search.

##### [S4] Downstream Knowledge Flows: The Feedback Nobody Routed

**Heading:** What the Signal Actually Contains > Terminology Divergence

**Chunk ID:** `wordpress:page:1486:chunk:v1:cf9e390b419ff1992c9eaba1b7a50f5c76fcd79934f3984905d3e5324043facd`

**Retrieval score:** `0.730469`

**Source text:**

Terminology divergence is a specific and underrecognized signal type, often hiding in plain sight as ticket volume on features that are technically documented but practically unfindable. A user searches for “payback tracking.” The documentation says “commission reconciliation.” The search returns nothing. The user opens a ticket. The documentation failure is invisible — not because the doc is wrong or missing, but because the language doesn’t match how the user thinks about the problem. This is a discoverability failure, not an accuracy failure, and the two require different fixes. High ticket volume on a well-documented feature is often the only signal that a terminology gap exists.

#### Retrieved context

1. **What Retrieval Systems Need from Your Content** — `0.906250`
   - Heading: Retrieval Depends on Consistent Signals
   - Chunk: `wordpress:page:2368:chunk:v1:ccba4172e13bcc89f3f437d7113db01f0f065827272dd12419d213cd9b0c1b97`

2. **How RAG Works in Retrieval-Based AI Systems** — `0.835938`
   - Heading: Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 4: Embeddings
   - Chunk: `wordpress:page:2366:chunk:v1:e608885ce1731409468b9d616ddc59062c0f90a8528615449f0a5d5202fe80e2`

3. **BM25** — `0.761719`
   - Heading: Why This Matters for Technical Writers
   - Chunk: `wordpress:glossary:2455:chunk:v1:3344c6d3a4216303c5a33e3ec0dcec38578fdc112dd395371636d429a3b30ae8`

4. **When and Why AI Retrieval Fails** — `0.757812`
   - Heading: Reason 2: The Wrong Source Looks More Relevant
   - Chunk: `wordpress:page:2374:chunk:v1:5da12b52a7c84ed10a1cb9202cb72746611312f6591f046df15f2aabd6e3c16f`

5. **Downstream Knowledge Flows: The Feedback Nobody Routed** — `0.730469`
   - Heading: What the Signal Actually Contains > Terminology Divergence
   - Chunk: `wordpress:page:1486:chunk:v1:cf9e390b419ff1992c9eaba1b7a50f5c76fcd79934f3984905d3e5324043facd`

---

### chunking-001 — PASS

**Category:** `exact_answer`

**Query:** Why is heading-aware chunking useful for documentation retrieval?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Heading-aware chunking uses a document's heading structure to keep related content and its section context together, producing more coherent units for retrieval.

#### Generated answer

Heading-aware chunking splits documentation along meaningful section boundaries and retains heading context, so each retrieved fragment is easier to interpret on its own. It helps preserve related content—such as prerequisites with procedures, warnings with affected steps, and explanations with tables—rather than separating it through arbitrary word-count splits. [S1][S2] Descriptive headings also give retrieval systems signals about a chunk’s topic and relevance, reducing the risk that needed information is buried in broad, mixed-topic sections. [S3]

#### Cited sources

##### [S1] How RAG Works in Retrieval-Based AI Systems

**Heading:** Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 3: Chunking

**Chunk ID:** `wordpress:page:2366:chunk:v1:a04b7e1517199858a707d7ce3829a7d00ba32e29593f8bd9a3bb3a51002f9022`

**Retrieval score:** `0.878906`

**Source text:**

Chunking is one of the most important and misunderstood parts of retrieval systems. Large documents usually aren’t retrieved as complete pages. Instead, they’re split into smaller pieces called chunks, and those chunks become the actual retrieval unit. This is one of the biggest conceptual shifts for documentation teams.

Users increasingly encounter fragments of documentation rather than navigating through full pages in sequence.

A chunk might contain:

- a short procedure
- a troubleshooting section
- a warning block
- a code example
- a conceptual explanation
- a subsection under an H2 or H3 heading

The chunking strategy matters because retrieval systems depend heavily on standalone comprehension. If a chunk loses too much context when separated from the surrounding page, retrieval quality suffers. This is also one of the places where human structural judgment matters most because the system itself cannot reliably determine where conceptual boundaries should begin or end. Retrieval-aware systems may automate the splitting process, but humans still shape the structure the system depends on through headings, hierarchy, layout decisions, and content organization.

This is why retrieval-aware systems often use heading-aware chunking or semantic chunking rather than splitting content arbitrarily every few hundred words.

The system is trying to preserve meaningful conceptual boundaries: a procedure should usually stay attached to its prerequisites; a warning should probably remain attached to the steps it warns about; and a table should ideally remain connected to the explanation that interprets it.

Weak chunking creates retrieval failures that look like AI failures. But the problem may have started much earlier.

##### [S2] Developing Chunking Strategies for AI Retrieval

**Heading:** Example: A help center article with an embedded PDF > Chunking the HTML article

**Chunk ID:** `wordpress:page:2567:chunk:v1:8f49d6560d0b5623d9d2979f98479a389a1f9a9ea50a99fec98010a5a7702fb4`

**Retrieval score:** `0.750000`

**Source text:**

The ingestion pipeline identifies the article as a help center procedure.

The chunking policy might:

- Start a new chunk at each major heading
- Keep a numbered sequence together when possible
- Keep a warning with the step it affects
- Add the article title and heading path to every chunk
- Use a size limit only when a section becomes too large

The resulting chunks might look like this:

Configure single sign-on
> Prerequisites

Configure single sign-on
> Configure your identity provider
> Steps 1–4

Configure single sign-on
> Configure your identity provider
> Steps 5–7
> Certificate warning

Configure single sign-on
> Troubleshoot sign-in failures

This is structure-aware chunking. The heading provides the first boundary, while a length limit handles unusually large sections.

##### [S3] What Retrieval Systems Need from Your Content

**Heading:** Retrieval Depends on Structure

**Chunk ID:** `wordpress:page:2368:chunk:v1:08bdd7fa2e2238343bfcc25ed2a171ac159b80d8b4be45e0399ee33ab53b078e`

**Retrieval score:** `0.703125`

**Source text:**

A retrieval system has to determine what a piece of content is about before it can decide whether that content is relevant to a query.

Structure provides many of those signals.

Clear headings, descriptive subheadings, logical section boundaries, and focused topics make it easier for retrieval systems to identify the purpose of a section and distinguish it from surrounding content. The same practices also make content easier for humans to scan and navigate, which is one reason retrieval-friendly content rarely feels different from well-written documentation.

Problems tend to appear when structure becomes vague. Generic headings such as “Overview,” “Configuration,” or “Additional Information” provide very little information about the content underneath them. Long sections that cover multiple topics create a similar challenge. A retrieval system may identify the section as relevant, but the actual information needed to answer the user’s question may be buried among several unrelated concepts.

Good structure doesn’t guarantee good retrieval and poor structure makes good retrieval much harder.

#### Retrieved context

1. **How RAG Works in Retrieval-Based AI Systems** — `0.878906`
   - Heading: Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 3: Chunking
   - Chunk: `wordpress:page:2366:chunk:v1:a04b7e1517199858a707d7ce3829a7d00ba32e29593f8bd9a3bb3a51002f9022`

2. **How RAG Works in Retrieval-Based AI Systems** — `0.761719`
   - Heading: Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 3: Chunking > Retrieval Systems Change How Documentation Gets Consumed
   - Chunk: `wordpress:page:2366:chunk:v1:5ed6b37bb9dda570a3b2f8d8fce4792504650298f57f08472db6cd2340d02c65`

3. **Developing Chunking Strategies for AI Retrieval** — `0.750000`
   - Heading: Example: A help center article with an embedded PDF > Chunking the HTML article
   - Chunk: `wordpress:page:2567:chunk:v1:8f49d6560d0b5623d9d2979f98479a389a1f9a9ea50a99fec98010a5a7702fb4`

4. **How RAG Works in Retrieval-Based AI Systems** — `0.710938`
   - Heading: Why the RAG Pipeline Matters for Documentation Teams > Retrieval Systems Change How Documentation Gets Consumed
   - Chunk: `wordpress:page:2366:chunk:v1:27efae7772d73e6bb29b3df77a8884ceb33969b06318fa7013ca58b99e8c7878`

5. **What Retrieval Systems Need from Your Content** — `0.703125`
   - Heading: Retrieval Depends on Structure
   - Chunk: `wordpress:page:2368:chunk:v1:08bdd7fa2e2238343bfcc25ed2a171ac159b80d8b4be45e0399ee33ab53b078e`

---

### metadata-001 — PASS

**Category:** `exact_answer`

**Query:** How can metadata improve AI retrieval?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Metadata gives retrieval systems information beyond the text itself that can help identify, filter, or select more appropriate content.
- Missing or inconsistent metadata can make it harder for the retrieval system to select the right content.

#### Generated answer

Metadata gives AI retrieval explicit signals that may be missing from the text itself—such as product/version applicability, intended audience, access permissions, content type, lifecycle status, ownership, and source authority. These signals let the system filter and rank results more accurately, for example by returning only current guidance for a specific product version or only content a user is permitted to access. [S1][S2][S3]

Consistent metadata also reduces noisy or irrelevant results across overlapping knowledge bases, duplicated procedures, and internal versus public content, while preserving traceability back to source material for citations. [S2][S4]

#### Cited sources

##### [S1] What Retrieval Systems Need from Your Content

**Heading:** Retrieval Depends on Information Beyond the Content Itself

**Chunk ID:** `wordpress:page:2368:chunk:v1:5920e764fa66d0574806063ab3d834080d7b1d6d281ec72cdba5baa02ad6aac4`

**Retrieval score:** `0.875000`

**Source text:**

Not all useful context appears in the body of a document.

A support article may apply only to enterprise customers. A procedure may be valid only for a particular product version. A troubleshooting guide may be relevant only to administrators.

Humans can sometimes infer those distinctions. Retrieval systems benefit when they are stated explicitly. That’s where metadata becomes important.

Depending on the platform, metadata may exist as frontmatter, tags, categories, XML attributes, JSON-LD, or custom content fields. The implementation varies across systems, but the purpose remains largely the same: provide information about the content that may not be obvious from the content alone.

Metadata helps establish relationships, scope, ownership, version applicability, and content type. It gives retrieval systems additional signals that can improve both retrieval quality and relevance.

Without those signals, retrieval systems are often forced to make assumptions that documentation teams could have expressed directly.

##### [S2] How RAG Works in Retrieval-Based AI Systems

**Heading:** Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 5: Vector Databases

**Chunk ID:** `wordpress:page:2366:chunk:v1:f7e1052ca169267580bdc5a9f56ba94f93c5cce1e722c6bed361f77915727a1c`

**Retrieval score:** `0.875000`

**Source text:**

After embeddings are created, they are stored inside a vector database.

A vector database stores:

- the chunk itself
- the chunk embedding
- associated metadata
- relationships back to the original source

This allows the system to rapidly compare semantic similarity between a user query and large collections of documentation chunks. The vector database isn’t storing “knowledge” in a human sense. It’s storing mathematical relationships tied back to source content.

This is also where metadata becomes retrieval infrastructure. Metadata is no longer just organizational labeling because it directly affects retrieval behavior. Although the filtering and lookup operations themselves are highly automated at this stage, the metadata model behind them is still shaped by human decisions about structure, governance, permissions, versioning, ownership, and trust boundaries long before retrieval begins.

For example, metadata may allow the system to:

- restrict results to a specific product version
- separate internal from public content
- filter by audience
- apply permissions-aware retrieval
- prioritize newer content over older content
- preserve source traceability for citations

Without metadata, retrieval systems often become noisy very quickly, especially in environments with:

- multiple product versions
- duplicated procedures
- overlapping knowledge bases
- internal and external documentation layers

At this point, the searchable knowledge environment has been built, and now the system has to search it.

##### [S3] When and Why AI Retrieval Fails

**Heading:** Reason 5: Metadata Is Missing or Inconsistent > What Needs to Be Fixed

**Chunk ID:** `wordpress:page:2374:chunk:v1:af19c2ce11e7a0a282f0411e953a0e0287368f596b3a0c0e7b0d58cf35dd18c3`

**Retrieval score:** `0.859375`

**Source text:**

Define a metadata model that matches the decisions the retrieval pipeline needs to make. Useful fields often include:

- product and feature
- version or release
- audience and access level
- content type
- lifecycle status
- owner and last reviewed date
- source authority

Apply the fields consistently through the publishing workflow. A small set of reliable values supports retrieval better than a complex taxonomy that teams use unevenly.

##### [S4] When and Why AI Retrieval Fails

**Heading:** Reason 5: Metadata Is Missing or Inconsistent

**Chunk ID:** `wordpress:page:2374:chunk:v1:17d2ea3b0d57327f2e279c4eee55a09cf315937ef49f7abc0e45c14627c97e94`

**Retrieval score:** `0.789062`

**Source text:**

The text of a page rarely contains every signal needed for filtering and ranking. A technically accurate paragraph may omit whether it applies to administrators, which version it covers, whether it’s current, or whether it represents approved guidance.

Metadata supplies those signals without forcing every paragraph to repeat them. Inconsistent values, missing fields, and free-form labels make the signals harder to apply across a documentation set.

#### Retrieved context

1. **What Retrieval Systems Need from Your Content** — `0.875000`
   - Heading: Retrieval Depends on Information Beyond the Content Itself
   - Chunk: `wordpress:page:2368:chunk:v1:5920e764fa66d0574806063ab3d834080d7b1d6d281ec72cdba5baa02ad6aac4`

2. **How RAG Works in Retrieval-Based AI Systems** — `0.875000`
   - Heading: Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 5: Vector Databases
   - Chunk: `wordpress:page:2366:chunk:v1:f7e1052ca169267580bdc5a9f56ba94f93c5cce1e722c6bed361f77915727a1c`

3. **When and Why AI Retrieval Fails** — `0.859375`
   - Heading: Reason 5: Metadata Is Missing or Inconsistent > What Needs to Be Fixed
   - Chunk: `wordpress:page:2374:chunk:v1:af19c2ce11e7a0a282f0411e953a0e0287368f596b3a0c0e7b0d58cf35dd18c3`

4. **When and Why AI Retrieval Fails** — `0.789062`
   - Heading: Reason 5: Metadata Is Missing or Inconsistent
   - Chunk: `wordpress:page:2374:chunk:v1:17d2ea3b0d57327f2e279c4eee55a09cf315937ef49f7abc0e45c14627c97e94`

5. **How RAG Works in Retrieval-Based AI Systems** — `0.777344`
   - Heading: Takeaways
   - Chunk: `wordpress:page:2366:chunk:v1:aef986c42ad2012660f687300872c5b2ed79d78d9618ecf69297b39d6c0d788b`

---

### bm25-001 — PASS

**Category:** `exact_answer`

**Query:** What is BM25 and how does it relate to semantic search?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- BM25 is a lexical or keyword-based retrieval method that ranks content based on how well query terms match the text.
- BM25 and semantic search use different signals: BM25 focuses on term matching, while semantic search focuses on meaning, so they can complement each other in retrieval.

#### Generated answer

BM25 (“Best Match 25”) is a keyword-based document-ranking algorithm. It scores relevance using term frequency in a document and how rare or common those terms are across the collection, so terms frequent in one document but rare overall are stronger signals. [S1]

It complements semantic search rather than replacing it: BM25 retrieves exact or near-exact term matches, while semantic search retrieves content based on meaning or conceptual similarity. Hybrid retrieval systems often use both, and can outperform either method alone by covering both precise terminology and differently worded queries. [S1][S2]

#### Cited sources

##### [S1] BM25

**Heading:** (none)

**Chunk ID:** `wordpress:glossary:2455:chunk:v1:346f83b867b5ec5041cec822a03b8a0ebe91d8c42a06474b98b777af09bee74c`

**Retrieval score:** `0.948302`

**Source text:**

BM25 (Best match 25) is a keyword-based ranking algorithm used in search systems to score how relevant a document is to a query. It works by analyzing term frequency, such as how often a search term appears in a document. It balances that that against how common the term is across the entire document collection. Terms that appear frequently in a specific document but rarely across the collection are treated as stronger relevance signals than terms that appear everywhere.

BM25 is one of the most widely used retrieval algorithms in traditional search systems and continues to play a role in modern AI search and retrieval pipelines, often alongside semantic search. Where semantic search finds content by meaning, BM25 finds content by exact and near-exact term matches. Using both together can improve retrieval quality by capturing relevance signals that either method alone might miss.

##### [S2] BM25

**Heading:** Common Confusion

**Chunk ID:** `wordpress:glossary:2455:chunk:v1:ce201f293c5218576275abf859abbaddc62d818dc515c3f252e8577e3622ea56`

**Retrieval score:** `0.911467`

**Source text:**

BM25 is sometimes assumed to be obsolete in AI-powered search, replaced entirely by semantic search and embeddings. In practice, many production retrieval systems use BM25 and semantic search together because they capture different kinds of relevance. BM25 excels at exact term matching; semantic search excels at conceptual similarity. Hybrid systems that combine both often outperform either approach used alone.

#### Retrieved context

1. **BM25** — `0.948302`
   - Heading: (none)
   - Chunk: `wordpress:glossary:2455:chunk:v1:346f83b867b5ec5041cec822a03b8a0ebe91d8c42a06474b98b777af09bee74c`

2. **BM25** — `0.911467`
   - Heading: Common Confusion
   - Chunk: `wordpress:glossary:2455:chunk:v1:ce201f293c5218576275abf859abbaddc62d818dc515c3f252e8577e3622ea56`

3. **BM25** — `0.853496`
   - Heading: Why This Matters for Technical Writers
   - Chunk: `wordpress:glossary:2455:chunk:v1:3344c6d3a4216303c5a33e3ec0dcec38578fdc112dd395371636d429a3b30ae8`

4. **TF-IDF** — `0.837509`
   - Heading: Common Confusion
   - Chunk: `wordpress:glossary:2458:chunk:v1:3057e8ffc022684599a627424be84a326617d7863b94148d53769c9c0938e9b6`

5. **Understanding RAG and Retrieval-Based AI Systems** — `0.721799`
   - Heading: Retrieval Systems Exist on a Spectrum > Traditional Lexical (Keyword-based) Retrieval
   - Chunk: `wordpress:page:2360:chunk:v1:1d260d234bb512c4e261ec340bf0733c5b0649a58e6b61badfb8718cc23666a5`

---

### rag-001 — PASS

**Category:** `exact_answer`

**Query:** What is retrieval-augmented generation?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Retrieval-augmented generation combines retrieval with generation: the system first retrieves relevant information and then uses that retrieved context to help generate an answer.

#### Generated answer

Retrieval-augmented generation (RAG) is an AI pattern that first retrieves relevant information from external sources—such as documents, databases, or knowledge bases—and then supplies it as context to a generative model to create a response. This lets the model produce answers grounded in current, specific, or proprietary information rather than relying only on what it learned during training. [S1][S2]

#### Cited sources

##### [S1] RAG

**Heading:** (none)

**Chunk ID:** `wordpress:glossary:1353:chunk:v1:7f830b37c170cf142826205ea04f1a0a57dc21b10ee04a981154281c10133447`

**Retrieval score:** `0.960938`

**Source text:**

Retrieval-augmented generation (RAG) is a technique that combines information retrieval with text generation. Instead of relying solely on what a language model learned during training, a RAG system first retrieves relevant content from an external source (i.e., a knowledge base, document repository, or database) and then uses that content to inform the generated response.

The result is a system that can produce contextually grounded answers based on current, specific, or proprietary information that the underlying model was never trained on. The model doesn’t “know” the retrieved content in the way it knows its training dat. It uses it in the moment to shape its output.

RAG is one of the primary architectural patterns behind AI search and retrieval products. When an AI search feature returns an answer grounded in your company’s internal documentation rather than general knowledge, RAG is typically what makes that possible.

##### [S2] Understanding RAG and Retrieval-Based AI Systems

**Heading:** What RAG Actually Is

**Chunk ID:** `wordpress:page:2360:chunk:v1:bc0b7d00c17d41eeb3790e1bd81258cb43d71038c5fef2a96abec5a964207af7`

**Retrieval score:** `0.949219`

**Source text:**

Retrieval-augmented generation (RAG) is an architectural pattern that allows AI systems to retrieve external information before generating a response.

Instead of relying only on information stored inside the model itself, a retrieval system can pull information from connected sources such as:

- documentation
- help centers
- APIs
- PDFs
- internal knowledge bases
- support articles
- databases
- business systems

That retrieved information is then provided to the model as additional context before the response is generated. This matters because large language models do not inherently have access to current organizational knowledge.

A model’s knowledge is fixed at training time, which means its responses reflect a snapshot of the world that may no longer be current. Organizations often need systems that can reference:

- changing documentation
- current operational procedures
- internal company information
- customer-specific data
- product releases
- private or proprietary knowledge

Retrieval helps bridge that gap. Instead of retraining a model every time information changes, organizations can update the underlying knowledge sources the retrieval system accesses.

#### Retrieved context

1. **RAG** — `0.960938`
   - Heading: (none)
   - Chunk: `wordpress:glossary:1353:chunk:v1:7f830b37c170cf142826205ea04f1a0a57dc21b10ee04a981154281c10133447`

2. **Understanding RAG and Retrieval-Based AI Systems** — `0.949219`
   - Heading: What RAG Actually Is
   - Chunk: `wordpress:page:2360:chunk:v1:bc0b7d00c17d41eeb3790e1bd81258cb43d71038c5fef2a96abec5a964207af7`

3. **Understanding RAG and Retrieval-Based AI Systems** — `0.906250`
   - Heading: Retrieval Systems Exist on a Spectrum > Retrieval Plus Generation
   - Chunk: `wordpress:page:2360:chunk:v1:2cf9922a60efbe0b073d85443befef720215c0d1eb4c0bdcce633c08ea63d9da`

4. **Documenting AI Search and Retrieval** — `0.890625`
   - Heading: Retrieval and Generation: Make the Boundary Visible
   - Chunk: `wordpress:page:815:chunk:v1:d0d89266a34cfee2835e1ff57ee20cf0dd6f39ca07b54365dc4d8de009a0a5f7`

5. **What Is AI Search and Retrieval?** — `0.839844`
   - Heading: Relationship to Other AI Categories
   - Chunk: `wordpress:page:811:chunk:v1:b0db3fdb7ffc4db4273358ac3248721fcddf66e479c9fabb44b2587f466f2b60`

---

### chunking-failure-001 — PASS

**Category:** `exact_answer`

**Query:** How can poor chunking reduce retrieval quality?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Poor chunking can break useful context or create chunks that are difficult for the retrieval system to interpret, making relevant information harder to retrieve accurately.

#### Generated answer

Poor chunking can split information in ways that remove the context needed to understand it. For example, a procedure may be separated from its prerequisites, a warning from the steps it applies to, or a table from its explanation. The resulting chunk may match a query but omit essential details such as the product name, prerequisite, limit, or required action. Arbitrary splits therefore create incomplete or vague retrieval units, reducing the relevance and usefulness of retrieved results. [S1][S2]

#### Cited sources

##### [S1] How RAG Works in Retrieval-Based AI Systems

**Heading:** Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 3: Chunking

**Chunk ID:** `wordpress:page:2366:chunk:v1:a04b7e1517199858a707d7ce3829a7d00ba32e29593f8bd9a3bb3a51002f9022`

**Retrieval score:** `0.878238`

**Source text:**

Chunking is one of the most important and misunderstood parts of retrieval systems. Large documents usually aren’t retrieved as complete pages. Instead, they’re split into smaller pieces called chunks, and those chunks become the actual retrieval unit. This is one of the biggest conceptual shifts for documentation teams.

Users increasingly encounter fragments of documentation rather than navigating through full pages in sequence.

A chunk might contain:

- a short procedure
- a troubleshooting section
- a warning block
- a code example
- a conceptual explanation
- a subsection under an H2 or H3 heading

The chunking strategy matters because retrieval systems depend heavily on standalone comprehension. If a chunk loses too much context when separated from the surrounding page, retrieval quality suffers. This is also one of the places where human structural judgment matters most because the system itself cannot reliably determine where conceptual boundaries should begin or end. Retrieval-aware systems may automate the splitting process, but humans still shape the structure the system depends on through headings, hierarchy, layout decisions, and content organization.

This is why retrieval-aware systems often use heading-aware chunking or semantic chunking rather than splitting content arbitrarily every few hundred words.

The system is trying to preserve meaningful conceptual boundaries: a procedure should usually stay attached to its prerequisites; a warning should probably remain attached to the steps it warns about; and a table should ideally remain connected to the explanation that interprets it.

Weak chunking creates retrieval failures that look like AI failures. But the problem may have started much earlier.

##### [S2] When and Why AI Retrieval Fails

**Heading:** Reason 1: The Content Is Too Hard to Interpret

**Chunk ID:** `wordpress:page:2374:chunk:v1:1fd0d122c85f543f202641b2c13dbe68eea1edd29fed0ba6e6cca9b671257731`

**Retrieval score:** `0.710586`

**Source text:**

Retrieval usually works with chunks rather than full pages. A paragraph that makes sense in context may become vague after it’s separated from the title, preceding steps, navigation path, screenshot, or nearby warning.

A reader can resolve references such as “this setting” by looking around the page. A retrieved passage has no such guarantee. It may match the query and still omit the product name, prerequisite, limit, or action the answer depends on.

#### Retrieved context

1. **How RAG Works in Retrieval-Based AI Systems** — `0.878238`
   - Heading: Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 3: Chunking
   - Chunk: `wordpress:page:2366:chunk:v1:a04b7e1517199858a707d7ce3829a7d00ba32e29593f8bd9a3bb3a51002f9022`

2. **How RAG Works in Retrieval-Based AI Systems** — `0.737708`
   - Heading: Phase 3: Generation — Constructing the Final Response > Step 10: Augmentation and Prompt Construction
   - Chunk: `wordpress:page:2366:chunk:v1:3310a5ae7b5638592162160ccaf5bdaf5da88754ba32737ce4613b8fe8fff8dd`

3. **How RAG Works in Retrieval-Based AI Systems** — `0.726169`
   - Heading: Takeaways
   - Chunk: `wordpress:page:2366:chunk:v1:aef986c42ad2012660f687300872c5b2ed79d78d9618ecf69297b39d6c0d788b`

4. **When and Why AI Retrieval Fails** — `0.710586`
   - Heading: Reason 1: The Content Is Too Hard to Interpret
   - Chunk: `wordpress:page:2374:chunk:v1:1fd0d122c85f543f202641b2c13dbe68eea1edd29fed0ba6e6cca9b671257731`

5. **How RAG Works in Retrieval-Based AI Systems** — `0.707096`
   - Heading: Phase 2: Retrieval — Searching the Knowledge Environment > Step 8: Retrieval
   - Chunk: `wordpress:page:2366:chunk:v1:a75220400fdcb6004a49da35d2cf309a91996c7dbd49f840c1a341ef2e076962`

---

### embeddings-001 — PASS

**Category:** `exact_answer`

**Query:** What role do embeddings play in semantic search?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Embeddings represent the meaning of content and queries as numerical vectors so semantic search can compare them by meaning rather than relying only on exact keyword matches.

#### Generated answer

Embeddings encode the meaning of queries and content as numerical vectors in a shared semantic space. Semantic search compares those vectors to retrieve content whose meaning is closest to the query, rather than requiring exact keyword matches. This lets it find conceptually related results even when they use different wording. [S1][S2][S3]

#### Cited sources

##### [S1] Embeddings

**Heading:** (none)

**Chunk ID:** `wordpress:glossary:2385:chunk:v1:d464f828b83a0321c8feb322073de1c3d4834cacba078308071454a17ca41f7c`

**Retrieval score:** `0.907072`

**Source text:**

Embeddings are numerical representations of text or other content like images or audio  that capture meaning in a form a machine can process and compare. When text is converted into an embedding, it becomes a series of numbers that position that text in a high-dimensional space. Content that is semantically similar ends up positioned close together in that space, even if the words used are completely different.

This is what allows an AI system to understand that “how do I reset my password” and “I can’t log in” are related questions without the two phrases sharing any words. The meaning is encoded in the numbers, not the text itself.

Embeddings are foundational to how many AI search and retrieval systems work, including RAG architectures. Rather than searching for exact keyword matches, these systems compare embeddings to find content that is conceptually relevant to a query.

##### [S2] Semantic Search

**Heading:** (none)

**Chunk ID:** `wordpress:glossary:2402:chunk:v1:f4f2d45eb19a9335d170a14231eab3437f16ec4922d3c39b7106e97b956546d4`

**Retrieval score:** `0.885186`

**Source text:**

Semantic search is a search approach that retrieves results based on the meaning of a query rather than exact keyword matches. Instead of looking for documents that contain the specific words a user typed, semantic search looks for content that is conceptually relevant, capturing intent and context rather than surface-level terms.

Capturing intent and context is made possible by embeddings, which encode meaning numerically so that similar concepts end up close together regardless of the words used to express them. A semantic search for “how do I cancel my subscription” can surface content about “ending a plan” or “account termination” without those phrases appearing in the query at all.

Semantic search is the retrieval mechanism behind many modern AI search products and is a foundational component of RAG architectures, where relevant content needs to be retrieved before a language model can generate a grounded response.

##### [S3] How RAG Works in Retrieval-Based AI Systems

**Heading:** Phase 2: Retrieval — Searching the Knowledge Environment > Step 7: Query Embedding

**Chunk ID:** `wordpress:page:2366:chunk:v1:5e62c38f1e45a880828f86c8efe27e3882fdeae298a59e3810b7fbb6499c8ff5`

**Retrieval score:** `0.838305`

**Source text:**

Once the query is prepared, it is converted into an embedding. The query now exists in the same semantic space as the documentation chunks created earlier. This allows the system to compare the user query mathematically against the stored content.

This is why retrieval systems can sometimes return conceptually related information even when exact wording differs. The system is looking for semantic proximity, not only matching keywords.

#### Retrieved context

1. **Embeddings** — `0.907072`
   - Heading: (none)
   - Chunk: `wordpress:glossary:2385:chunk:v1:d464f828b83a0321c8feb322073de1c3d4834cacba078308071454a17ca41f7c`

2. **Semantic Search** — `0.885186`
   - Heading: (none)
   - Chunk: `wordpress:glossary:2402:chunk:v1:f4f2d45eb19a9335d170a14231eab3437f16ec4922d3c39b7106e97b956546d4`

3. **How RAG Works in Retrieval-Based AI Systems** — `0.851206`
   - Heading: Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 4: Embeddings
   - Chunk: `wordpress:page:2366:chunk:v1:e608885ce1731409468b9d616ddc59062c0f90a8528615449f0a5d5202fe80e2`

4. **How RAG Works in Retrieval-Based AI Systems** — `0.838305`
   - Heading: Phase 2: Retrieval — Searching the Knowledge Environment > Step 7: Query Embedding
   - Chunk: `wordpress:page:2366:chunk:v1:5e62c38f1e45a880828f86c8efe27e3882fdeae298a59e3810b7fbb6499c8ff5`

5. **Vector Database** — `0.828080`
   - Heading: (none)
   - Chunk: `wordpress:glossary:2391:chunk:v1:34fb4718fa1ea1e2c03bcb754e53c06edabbcb426342a2c3d283d5cb4e9843dd`

---

### documentation-engineering-001 — PASS

**Category:** `confusable`

**Query:** What does a documentation engineer do?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- A documentation engineer works on the systems that make documentation function reliably, not only on producing individual documents.
- The role spans both documentation architecture and practical implementation or operations, connecting system design with workflows, tooling, and infrastructure.

#### Generated answer

A documentation engineer designs the knowledge system that documentation lives in and builds or configures the operational machinery that enforces that design. The work includes documentation strategy, audience journeys, information architecture, taxonomy, metadata, content models, governance, standards, search and retrieval requirements, versioning, localization, and lifecycle design; then integrating and automating tooling to carry those decisions out. [S1][S2]

They also maintain a feedback loop: operational data and problems inform improvements to the architecture. [S3][S4]

#### Cited sources

##### [S1] Documentation Engineering

**Heading:** What the Discipline Spans

**Chunk ID:** `wordpress:page:2672:chunk:v1:87abbcd779d51ab1efff333a0143c52e07404387664727ce45cd1bc51db7cbf7`

**Retrieval score:** `0.921713`

**Source text:**

Documentation engineering is defined less by a fixed list of tasks than by what it spans. It sits across the boundary between the two layers of the knowledge infrastructure, and the spanning is the point.

On one side is the architectural layer, the design of how the knowledge system should work and what governs it. That covers:

- documentation strategy and how it aligns with what the product is trying to do;
- the audiences, journeys, and boundaries of the content;
- information architecture, taxonomy, metadata, and content models; governance , ownership, standards, and definitions of done;
- style, terminology, and reusable patterns; the requirements for search, retrieval, AI-readiness, and analytics;
- and the principles for versioning, localization, and the content lifecycle.

It’s the work of deciding what the system should be.

On the other side is the operations infrastructure , the machinery that turns those decisions into a working system. Designing, configuring, building, integrating, and automating the tooling so it enforces the architecture instead of drifting from it. The documentation engineer’s relationship to it is specific: they make sure it embodies the design rather than quietly replacing it with whatever the tools default to.

The role is the spanning itself. A pure strategist who hands a design to someone else to build loses control of it at the exact point where implementation choices silently rewrite the design. A pure toolsmith who automates without owning the design builds a fast, well-run system with no particular reason to be shaped the way it is. Documentation engineering is the job that holds both ends: designing the architecture, then making the machinery carry it out.

##### [S2] Documentation Engineering

**Heading:** (none)

**Chunk ID:** `wordpress:page:2672:chunk:v1:c766bea21181124ceef5606d32b1484f1417fede0791f2a1cc94bd744799f60d`

**Retrieval score:** `0.898698`

**Source text:**

Documentation engineering, where the term is recognized at all, usually gets read as the technical craft of producing docs: the tooling, the pipelines, docs-as-code . That reading captures part of the job.

The discipline as a whole is organized around a different task: designing the knowledge system that content lives in. Documentation engineering is the discipline that designs the knowledge system content lives in — spanning both the architectural layer (strategy, taxonomy, governance, content models) and the operations infrastructure that carries that design out . What sets it apart from adjacent roles is that it owns both ends as one job: deciding what the system should be, and building the machinery that makes it actually work that way, rather than handing off one side or the other.

Every earlier section of this series mapped a system that mostly wasn’t designed: the tiers of knowledge and how each one fails, the flows that carry knowledge or lose it, the audiences the system serves and where it serves them badly. What’s left, and where the series lands, is the discipline responsible for designing the thing all of it describes.

##### [S3] Documentation Engineering

**Heading:** Takeaways

**Chunk ID:** `wordpress:page:2672:chunk:v1:e6900d03c9efe2af2bcf4421adc390cc2f01e2ff036c3166146014d5b9e77f0d`

**Retrieval score:** `0.886485`

**Source text:**

- Documentation engineering is the discipline that designs the knowledge system. It spans the architectural layer, how the system should work, and the operations infrastructure, the machinery that runs it. The spanning is what defines it.
- “Today” marks a shift in the field’s center of gravity, from producing content to designing the system content lives in. The craft of writing still matters; the discipline is a layer added above it, not a replacement for it.
- The feedback loop between architecture and operations is a core practice: the architecture defines the machinery, the machinery reveals problems, and that evidence reshapes the architecture. It’s the loop downstream signal is meant to travel.
- The discipline overlaps with technical writing, content strategy, DocOps, information architecture, and knowledge management, and differs from each by spanning both the design and the implementation of the product knowledge system.
- Content modeling is a signature competency, alongside information architecture, governance design, retrieval and AI-readiness, and analytics. The rare, defining skill is holding design intent and implementation reality together.
- Documentation engineering is a set of responsibilities before it’s a job title. One person owns it at a small company; a team of specialists shares it at a large one. Left unassigned, those responsibilities default to no one, which is where most of the series’ gaps come from.

##### [S4] The Knowledge Infrastructure

**Heading:** Documentation Engineering Spans Architecture and Operations Layers

**Chunk ID:** `wordpress:page:2647:chunk:v1:d6663229376cac5076072c319c3116d3af5f183913fac54e63db3efb3472cfd1`

**Retrieval score:** `0.863756`

**Source text:**

Documentation engineering is the discipline that sits across the boundary between both the architecture and operations layers. It designs the architectural layer, then makes sure the operations infrastructure embodies those decisions rather than drifting from them. The spanning is what defines the role. Designing the system and building what enforces the design are held together in one discipline, instead of split between a strategist who hands off a plan and a toolsmith who automates without owning it.

Its scope is the whole system this series has mapped. Every gap named across the earlier sections has the same shape underneath. Ephemeral knowledge is lost because nothing captures it, evergreen content drifts because nothing governs its retirement, audiences stay siloed because no shared model was designed, and downstream signal never routes back. Each is an architectural decision that was never made, which the operations infrastructure was then built to serve anyway. Documentation engineering is the discipline that makes those decisions.

The two layers connect through a continuous loop rather than a one-time handoff. The architecture defines the operations, the operations produce data and surface problems, and what that data reveals feeds back into the architecture. Keeping that loop turning is part of the discipline, and it’s where this section reconnects to the downstream feedback the series has already described.

How the role actually looks, from one person owning all of it at a small company to a set of responsibilities shared across specialists at a large one, and what the shift toward it means for technical writers, is the subject of the second article.

#### Retrieved context

1. **Documentation Engineering** — `0.921713`
   - Heading: What the Discipline Spans
   - Chunk: `wordpress:page:2672:chunk:v1:87abbcd779d51ab1efff333a0143c52e07404387664727ce45cd1bc51db7cbf7`

2. **Documentation Engineering** — `0.898698`
   - Heading: (none)
   - Chunk: `wordpress:page:2672:chunk:v1:c766bea21181124ceef5606d32b1484f1417fede0791f2a1cc94bd744799f60d`

3. **Documentation Engineering** — `0.886485`
   - Heading: Takeaways
   - Chunk: `wordpress:page:2672:chunk:v1:e6900d03c9efe2af2bcf4421adc390cc2f01e2ff036c3166146014d5b9e77f0d`

4. **Developing Chunking Strategies for AI Retrieval** — `0.867627`
   - Heading: What the collaboration looks like > The documentation engineer describes the content
   - Chunk: `wordpress:page:2567:chunk:v1:fe540711b22cd8a91e3d3371ee353c9fa830683be708159fc109c0073b4816a1`

5. **The Knowledge Infrastructure** — `0.863756`
   - Heading: Documentation Engineering Spans Architecture and Operations Layers
   - Chunk: `wordpress:page:2647:chunk:v1:d6663229376cac5076072c319c3116d3af5f183913fac54e63db3efb3472cfd1`

**Dataset note:** The current top-ranked chunk is the substantive What the Discipline Spans section.

---

### documentation-engineering-002 — PASS

**Category:** `exact_answer`

**Query:** What is documentation engineering?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Documentation engineering is the discipline of designing and building the systems that support how documentation is created, managed, delivered, and maintained.
- It shifts the focus from producing individual pieces of content to designing the larger documentation system.

#### Generated answer

Documentation engineering is the discipline of designing the knowledge system that documentation lives in and building the operational infrastructure that makes that design work. It spans both the architectural layer—such as strategy, information architecture, taxonomy, governance, and content models—and the tooling, automation, and operations that implement and enforce it. Its defining responsibility is holding design intent and implementation together, using operational feedback to improve the system over time. It adds a systems-design layer above, rather than replaces, the work of writing documentation. [S1] [S2]

#### Cited sources

##### [S1] Documentation Engineering

**Heading:** Takeaways

**Chunk ID:** `wordpress:page:2672:chunk:v1:e6900d03c9efe2af2bcf4421adc390cc2f01e2ff036c3166146014d5b9e77f0d`

**Retrieval score:** `0.945312`

**Source text:**

- Documentation engineering is the discipline that designs the knowledge system. It spans the architectural layer, how the system should work, and the operations infrastructure, the machinery that runs it. The spanning is what defines it.
- “Today” marks a shift in the field’s center of gravity, from producing content to designing the system content lives in. The craft of writing still matters; the discipline is a layer added above it, not a replacement for it.
- The feedback loop between architecture and operations is a core practice: the architecture defines the machinery, the machinery reveals problems, and that evidence reshapes the architecture. It’s the loop downstream signal is meant to travel.
- The discipline overlaps with technical writing, content strategy, DocOps, information architecture, and knowledge management, and differs from each by spanning both the design and the implementation of the product knowledge system.
- Content modeling is a signature competency, alongside information architecture, governance design, retrieval and AI-readiness, and analytics. The rare, defining skill is holding design intent and implementation reality together.
- Documentation engineering is a set of responsibilities before it’s a job title. One person owns it at a small company; a team of specialists shares it at a large one. Left unassigned, those responsibilities default to no one, which is where most of the series’ gaps come from.

##### [S2] Documentation Engineering

**Heading:** What the Discipline Spans

**Chunk ID:** `wordpress:page:2672:chunk:v1:87abbcd779d51ab1efff333a0143c52e07404387664727ce45cd1bc51db7cbf7`

**Retrieval score:** `0.941406`

**Source text:**

Documentation engineering is defined less by a fixed list of tasks than by what it spans. It sits across the boundary between the two layers of the knowledge infrastructure, and the spanning is the point.

On one side is the architectural layer, the design of how the knowledge system should work and what governs it. That covers:

- documentation strategy and how it aligns with what the product is trying to do;
- the audiences, journeys, and boundaries of the content;
- information architecture, taxonomy, metadata, and content models; governance , ownership, standards, and definitions of done;
- style, terminology, and reusable patterns; the requirements for search, retrieval, AI-readiness, and analytics;
- and the principles for versioning, localization, and the content lifecycle.

It’s the work of deciding what the system should be.

On the other side is the operations infrastructure , the machinery that turns those decisions into a working system. Designing, configuring, building, integrating, and automating the tooling so it enforces the architecture instead of drifting from it. The documentation engineer’s relationship to it is specific: they make sure it embodies the design rather than quietly replacing it with whatever the tools default to.

The role is the spanning itself. A pure strategist who hands a design to someone else to build loses control of it at the exact point where implementation choices silently rewrite the design. A pure toolsmith who automates without owning the design builds a fast, well-run system with no particular reason to be shaped the way it is. Documentation engineering is the job that holds both ends: designing the architecture, then making the machinery carry it out.

#### Retrieved context

1. **Documentation Engineering** — `0.945312`
   - Heading: Takeaways
   - Chunk: `wordpress:page:2672:chunk:v1:e6900d03c9efe2af2bcf4421adc390cc2f01e2ff036c3166146014d5b9e77f0d`

2. **Documentation Engineering** — `0.941406`
   - Heading: What the Discipline Spans
   - Chunk: `wordpress:page:2672:chunk:v1:87abbcd779d51ab1efff333a0143c52e07404387664727ce45cd1bc51db7cbf7`

3. **Documentation Engineering** — `0.933594`
   - Heading: (none)
   - Chunk: `wordpress:page:2672:chunk:v1:c766bea21181124ceef5606d32b1484f1417fede0791f2a1cc94bd744799f60d`

4. **Documentation Engineering** — `0.914062`
   - Heading: From Producing Content to Designing Systems
   - Chunk: `wordpress:page:2672:chunk:v1:f3d8001bbc75f33400e9de7bdabd684d2d1cd22999a62fe294c3f05383debb32`

5. **The Knowledge Infrastructure** — `0.914062`
   - Heading: Documentation Engineering Spans Architecture and Operations Layers
   - Chunk: `wordpress:page:2647:chunk:v1:d6663229376cac5076072c319c3116d3af5f183913fac54e63db3efb3472cfd1`

---

### context-001 — PASS

**Category:** `ambiguous`

**Query:** How important is context in documentation?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Context is important because it gives readers the surrounding information they need to understand and apply documentation correctly.

#### Generated answer

Context is highly important because readers often enter documentation midstream and need to quickly determine whether a section is relevant. It reduces guesswork, helps prevent misuse by clarifying when information applies, and makes instructions understandable rather than detached from their purpose. [S1][S2]

Its amount should be calibrated to the audience: it is especially important for new users and user-facing material, while experienced internal audiences usually need only lightweight orientation. [S3] Context also matters for retrieval-based access, where isolated sections may be surfaced without their surrounding page; key concepts should therefore be explicit enough for each section to stand alone. [S4]

#### Cited sources

##### [S1] Context Setting in Documentation

**Heading:** Why This Matters

**Chunk ID:** `wordpress:page:252:chunk:v1:6df1776ad2accd5b22bcf979fb5477dbaeaabe485ee70acba1b77fc98c04d2ec`

**Retrieval score:** `0.937500`

**Source text:**

Most documentation is opened midstream. Readers are not reading from the beginning of a manual. They are scanning for something specific.

If you begin immediately with steps, configuration details, or definitions, readers have to infer relevance.

Context reduces that guesswork. It helps readers decide quickly whether they should proceed, skim, or stop.

It also prevents misuse. When people understand when something applies, they are less likely to apply it in the wrong situation.

##### [S2] Context Setting in Documentation

**Heading:** What Is Context Setting?

**Chunk ID:** `wordpress:page:252:chunk:v1:3cf84d8e7f9c02142218d16ae517d63ca9ef5e0ea2ad86c8f79d551add895a2d`

**Retrieval score:** `0.902344`

**Source text:**

Context setting means you explain when and why something matters before explaining how it works. It orients the reader. It answers the quiet question behind most documentation use: “Is this relevant to me?”

Context setting isn’t the same as explaining why a specific step exists. That practice belongs to “Why and When Steps.” Context setting happens before the steps begin. It frames the situation so the reader understands whether the entire section applies to them at all.

Without context, instructions float. But with context, they land.

##### [S3] Context Setting in Documentation

**Heading:** Where Does Context Setting Apply?

**Chunk ID:** `wordpress:page:252:chunk:v1:f72d83b8d9fbfbe1ea1c73b051775c9e5b2fd179eb82468c1c98423d87201942`

**Retrieval score:** `0.890625`

**Source text:**

This principle is essential in user-facing documentation, onboarding material, and any content written for readers who are new to a system, concept, or workflow. When readers lack context, they have to construct it themselves, which increases effort and creates room for misunderstanding.

In internal knowledge bases written for experienced teams, apply this principle with calibration. Over-explaining context your audience already has can feel condescending and makes documentation slower to use. For internal docs, favor lightweight orientation — enough to situate the reader — over full background explanations.

In API reference documentation, context setting belongs at the section or endpoint level, not before every parameter. A brief explanation of what a resource represents or when a method is appropriate is usually sufficient.

##### [S4] What Retrieval Systems Need from Your Content

**Heading:** Retrieval Depends on Context

**Chunk ID:** `wordpress:page:2368:chunk:v1:37f14f932cb405c3617c905302fab4a35fccb2791fdebcb69a83516c9a9e2547`

**Retrieval score:** `0.863281`

**Source text:**

One of the biggest shifts retrieval introduces is that users no longer encounter documentation in the order writers intended.

A reader navigating a help center can move through surrounding pages, follow links, and gradually build context. Retrieval systems often surface only a portion of a larger document. A generated answer, a few paragraphs, or a single retrieved section may be all the user sees.

Content that depends heavily on surrounding context becomes harder to interpret once it leaves the page where it was originally written.

Consider a sentence such as:

This setting controls how long it remains active.

A reader who has followed the page from the beginning may know exactly what “this setting” refers to. A retrieval system may surface only that paragraph. The missing context never arrives.

The issue isn’t that retrieval systems are incapable of understanding the content. The issue is that important information was stored outside the section that needed it.

Documentation doesn’t need to repeat itself constantly. It does need to make important concepts, features, products, and workflows explicit enough that individual sections remain understandable when surfaced independently.

#### Retrieved context

1. **Context Setting in Documentation** — `0.937500`
   - Heading: Why This Matters
   - Chunk: `wordpress:page:252:chunk:v1:6df1776ad2accd5b22bcf979fb5477dbaeaabe485ee70acba1b77fc98c04d2ec`

2. **Context Setting in Documentation** — `0.902344`
   - Heading: What Is Context Setting?
   - Chunk: `wordpress:page:252:chunk:v1:3cf84d8e7f9c02142218d16ae517d63ca9ef5e0ea2ad86c8f79d551add895a2d`

3. **Context Setting in Documentation** — `0.890625`
   - Heading: Where Does Context Setting Apply?
   - Chunk: `wordpress:page:252:chunk:v1:f72d83b8d9fbfbe1ea1c73b051775c9e5b2fd179eb82468c1c98423d87201942`

4. **Documenting AI Assistants, Copilots, and Agents** — `0.863281`
   - Heading: Explain the Role of Context
   - Chunk: `wordpress:page:143:chunk:v1:63f071a4c2a8991aa1cbf250c2fc2d0704fecda4f4333e781b3e6fef81e85bbd`

5. **What Retrieval Systems Need from Your Content** — `0.863281`
   - Heading: Retrieval Depends on Context
   - Chunk: `wordpress:page:2368:chunk:v1:37f14f932cb405c3617c905302fab4a35fccb2791fdebcb69a83516c9a9e2547`

---

### cms-selection-001 — PASS

**Category:** `confusable`

**Query:** How do I choose a CMS for documentation?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Choose a documentation content system based on the documentation team's needs, workflows, and the problems the system needs to solve rather than treating it only as a writing-tool choice.
- Different types of content management platforms support different documentation needs, so the choice should fit the team's content structure, publishing, collaboration, and operational requirements.

#### Generated answer

Choose a CMS based on the documentation environment you need to operate—not on feature count, existing licensing, or short-term publishing convenience. Assess your product complexity, content structure, contributors and ownership, review/governance workflows, publishing needs, and long-term maintenance requirements. [S1][S2]

A lighter, article-oriented system fits fast publishing, lightweight contributions, and support-style content. A structured CCMS is better when you need large or multi-product documentation sets, versioning, reusable and conditional content, formal reviews, diverse outputs, and scalable maintenance; it requires more process discipline and upfront content modeling. [S1][S3]

If documentation is part of a broader omnichannel content ecosystem, an enterprise CMS may suit API-first delivery and digital-experience integrations, but expect to build or customize documentation-specific editorial and governance workflows. [S4]

There is no universally best choice: select the platform whose operating assumptions match how your team must create, govern, publish, and maintain documentation over time. [S2][S5]

#### Cited sources

##### [S1] How to Choose a CCMS Based on Your Documentation Needs

**Heading:** A CCMS Isn’t Just a Writing Tool Decision

**Chunk ID:** `wordpress:post:1938:chunk:v1:c1831e22bca471cd88f2ee9abfec94553bd0b5f6af2a4d40fea70fe18586dc3b`

**Retrieval score:** `0.857723`

**Source text:**

A lot of CCMS conversations focus heavily on features. Can the system publish to multiple outputs? Does it support reusable content? Is there version history? Does it integrate with review workflows? Those questions matter. But they are only part of the decision.

A documentation platform is also an operational system that shapes how documentation moves through the organization over time, including:

- how content gets reviewed
- who participates in documentation work
- how governance scales
- how reusable content is managed
- how updates are maintained
- how knowledge moves between teams
- how easily documentation stays aligned with a changing product

This is where organizations often underestimate the long-term impact of a documentation platform decision.

A system that works well for lightweight support articles may become difficult once the documentation environment requires:

- structured reuse
- stronger review workflows
- formal ownership
- multi-product documentation sets
- versioning across releases
- conditional content
- long-term maintenance visibility

The opposite can also happen. A heavily structured platform can introduce unnecessary process and operational overhead for a smaller team that primarily needs fast publishing, lightweight contribution, and simple support-style content.

That’s why the question isn’t simply:

Which platform has the most features?

The more important question is:

What kind of documentation environment are we actually operating?

Every documentation platform carries assumptions about how documentation work happens.

Some systems assume:

- fast publishing matters most
- many contributors need lightweight access
- support workflows are central
- content is mostly article-oriented

Others assume:

- reuse matters deeply
- governance complexity will increase
- documentation sets will scale over time
- publishing outputs will diversify
- content relationships need structure

##### [S2] How to Choose a CCMS Based on Your Documentation Needs

**Heading:** Documentation Systems Shape How Teams Work

**Chunk ID:** `wordpress:post:1938:chunk:v1:23309d30167b3a98d3be9b51f674b0b58744a04ea98e38f9e628421694c0ac63`

**Retrieval score:** `0.802486`

**Source text:**

Documentation systems aren’t neutral. They shape how teams collaborate, how reviews happen, how governance scales, how reusable content is managed, and how easily documentation stays aligned with the product over time.

That’s why choosing a CCMS based primarily on convenience, existing licensing, or short-term publishing needs often creates operational friction later.

The goal isn’t to find a universally perfect platform. The goal is to choose a system aligned with the actual documentation environment the organization is building: the complexity of the product, the structure of the content, the people involved in maintaining it, and the workflows required to keep it useful over time. Organizations aren’t just choosing a tool; they are choosing the operational assumptions their documentation system will carry for years afterward.

##### [S3] How to Choose a CCMS Based on Your Documentation Needs

**Heading:** Different CCMS Categories Solve Different Problems > Traditional structured CCMS platforms

**Chunk ID:** `wordpress:post:1938:chunk:v1:c8aca29f6f534499a5cf7f602286ebc893262b382cb57e84ad5372e4dac610e8`

**Retrieval score:** `0.780672`

**Source text:**

Platforms like Paligo or Oxygen XML Author with a CMS layer were designed around structure, reuse, governance, and long-term scalability.

These systems are usually strongest when documentation environments involve:

- large documentation sets
- multiple products or versions
- reusable components
- conditional content
- formal review and publishing workflows
- long-term maintenance complexity

Their strength is control. The tradeoff is that they can feel heavier operationally. They often require stronger process discipline, more upfront structure, and more intentional content modeling than lighter platforms.

For organizations with growing documentation complexity, however, that structure can become necessary rather than burdensome.

##### [S4] How to Choose a CCMS Based on Your Documentation Needs

**Heading:** Different CCMS Categories Solve Different Problems > Enterprise CMS platforms adapted for documentation

**Chunk ID:** `wordpress:post:1938:chunk:v1:06090cf3d6bd44824350eb5a1bbfb5e94248398500de1cd40771aa8beddf023f`

**Retrieval score:** `0.803548`

**Source text:**

Some organizations use broader enterprise CMS platforms such as Adobe Experience Manager or Contentful for documentation delivery. These systems are often strongest when documentation exists inside a larger omnichannel content ecosystem.

Their strengths may include:

- API-first delivery
- broader ecosystem integration
- flexible content delivery models
- integration with digital experience systems

But they are usually not designed specifically around documentation-team workflows.m That often means organizations must build or customize parts of the editorial and governance experience themselves.

##### [S5] How to Choose a CCMS Based on Your Documentation Needs

**Heading:** (none)

**Chunk ID:** `wordpress:post:1938:chunk:v1:1e8bd284d05914e3b7ef1433e02a5b200ea0e266fb0944205619742a51933529`

**Retrieval score:** `0.791275`

**Source text:**

The quick version: There is no universally “best” CCMS . Different documentation platforms are designed around different assumptions about structure, governance , collaboration, publishing, maintenance, and scale. A system that works well for support-oriented knowledge sharing may become painful for complex product documentation over time, while a heavily structured platform may create unnecessary overhead for smaller or simpler documentation environments. The real question isn’t which platform has the most features, it’s whether the platform matches the actual documentation environment your organization is building.

This article focuses primarily on end-user product documentation environments. API and developer documentation often operate under different technical and workflow constraints, including docs-as-code workflows, schema-driven publishing, and tighter integration with engineering systems.

#### Retrieved context

1. **How to Choose a CCMS Based on Your Documentation Needs** — `0.857723`
   - Heading: A CCMS Isn’t Just a Writing Tool Decision
   - Chunk: `wordpress:post:1938:chunk:v1:c1831e22bca471cd88f2ee9abfec94553bd0b5f6af2a4d40fea70fe18586dc3b`

2. **How to Choose a CCMS Based on Your Documentation Needs** — `0.803548`
   - Heading: Different CCMS Categories Solve Different Problems > Enterprise CMS platforms adapted for documentation
   - Chunk: `wordpress:post:1938:chunk:v1:06090cf3d6bd44824350eb5a1bbfb5e94248398500de1cd40771aa8beddf023f`

3. **How to Choose a CCMS Based on Your Documentation Needs** — `0.802486`
   - Heading: Documentation Systems Shape How Teams Work
   - Chunk: `wordpress:post:1938:chunk:v1:23309d30167b3a98d3be9b51f674b0b58744a04ea98e38f9e628421694c0ac63`

4. **How to Choose a CCMS Based on Your Documentation Needs** — `0.791275`
   - Heading: (none)
   - Chunk: `wordpress:post:1938:chunk:v1:1e8bd284d05914e3b7ef1433e02a5b200ea0e266fb0944205619742a51933529`

5. **How to Choose a CCMS Based on Your Documentation Needs** — `0.780672`
   - Heading: Different CCMS Categories Solve Different Problems > Traditional structured CCMS platforms
   - Chunk: `wordpress:post:1938:chunk:v1:c8aca29f6f534499a5cf7f602286ebc893262b382cb57e84ad5372e4dac610e8`

**Dataset note:** The top articles are all from the CCMS-selection article.

---

### unanswerable-kubernetes-001 — PASS

**Category:** `unanswerable`

**Query:** How do I configure Kubernetes horizontal pod autoscaling?

**Expected sufficient evidence:** `false`

**Actual sufficient evidence:** `false`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `false`

#### Required points for qualitative review

None.

#### Generated answer

The available sources are insufficient to explain how to configure Kubernetes horizontal pod autoscaling.

#### Cited sources

No cited sources.

#### Retrieved context

No results passed the retrieval support gate.

---

### unanswerable-cooking-001 — PASS

**Category:** `unanswerable`

**Query:** How long should I roast a whole chicken?

**Expected sufficient evidence:** `false`

**Actual sufficient evidence:** `false`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `false`

#### Required points for qualitative review

None.

#### Generated answer

The available sources are insufficient to determine how long to roast a whole chicken.

#### Cited sources

No cited sources.

#### Retrieved context

No results passed the retrieval support gate.

---

### unanswerable-developer-transition-001 — PASS

**Category:** `unanswerable`

**Query:** How do I transition from technical writer to software developer

**Expected sufficient evidence:** `false`

**Actual sufficient evidence:** `false`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `false`

#### Required points for qualitative review

None.

#### Generated answer

The available sources are insufficient to answer this question.

#### Cited sources

No cited sources.

#### Retrieved context

No results passed the retrieval support gate.

**Dataset note:** Current retrieval returns nothing.

---

### unanswerable-hybrid-implementation-001 — PASS

**Category:** `unanswerable`

**Query:** How do I implement hybrid search with BM25 and vector search in Python?

**Expected sufficient evidence:** `false`

**Actual sufficient evidence:** `false`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `false`

#### Required points for qualitative review

None.

#### Generated answer

The available sources are insufficient to provide a grounded implementation of hybrid BM25 and vector search in Python.

#### Cited sources

No cited sources.

#### Retrieved context

No results passed the retrieval support gate.

**Dataset note:** The corpus discusses BM25, semantic search, and hybrid retrieval conceptually but does not provide a Python implementation.

---

### unanswerable-vector-db-selection-001 — PASS

**Category:** `unanswerable`

**Query:** How do I choose between Qdrant and Pinecone for a documentation RAG system?

**Expected sufficient evidence:** `false`

**Actual sufficient evidence:** `false`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `false`

#### Required points for qualitative review

None.

#### Generated answer

The available sources are insufficient to compare Qdrant and Pinecone for a documentation RAG system.

#### Cited sources

No cited sources.

#### Retrieved context

No results passed the retrieval support gate.

**Dataset note:** The corpus discusses vector databases and retrieval architecture but does not compare Qdrant and Pinecone.

---

### unanswerable-embedding-finetuning-001 — PASS

**Category:** `unanswerable`

**Query:** How do I fine-tune an embedding model on technical documentation?

**Expected sufficient evidence:** `false`

**Actual sufficient evidence:** `false`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `false`

#### Required points for qualitative review

None.

#### Generated answer

The available sources are insufficient to answer how to fine-tune an embedding model on technical documentation.

#### Cited sources

No cited sources.

#### Retrieved context

No results passed the retrieval support gate.

**Dataset note:** The corpus explains embeddings and semantic retrieval but does not explain how to fine-tune an embedding model.

---

### unanswerable-cms-migration-001 — PASS

**Category:** `unanswerable`

**Query:** How do I migrate documentation from WordPress to a headless CMS?

**Expected sufficient evidence:** `false`

**Actual sufficient evidence:** `false`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `false`

#### Required points for qualitative review

None.

#### Generated answer

The available sources are insufficient to provide a grounded migration process for moving documentation from WordPress to a headless CMS.

#### Cited sources

No cited sources.

#### Retrieved context

No results passed the retrieval support gate.

**Dataset note:** The corpus discusses documentation platforms and CMS selection but does not provide a WordPress-to-headless-CMS migration procedure.

---

### unanswerable-doc-engineering-certification-001 — PASS

**Category:** `unanswerable`

**Query:** What certification should I get to become a documentation engineer?

**Expected sufficient evidence:** `false`

**Actual sufficient evidence:** `false`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `false`

#### Required points for qualitative review

None.

#### Generated answer

The available sources are insufficient to determine which certification is recommended for becoming a documentation engineer.

#### Cited sources

No cited sources.

#### Retrieved context

No results passed the retrieval support gate.

**Dataset note:** The corpus discusses documentation engineering and career evolution but does not recommend certifications for becoming a documentation engineer.

---

### synonym-001 — PASS

**Category:** `synonym`

**Query:** How can AI search recognize that two differently worded questions mean the same thing?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Semantic search can match differently worded questions by representing their meaning rather than relying only on exact words.
- Embeddings place semantically similar queries and content near each other in vector space, which lets the system recognize similar meaning even when the wording differs.

#### Generated answer

AI search can use embeddings: numerical representations that encode a question’s meaning. It converts questions into vectors in a shared semantic space and compares their proximity; differently worded questions with similar intent tend to be close together, so the system can recognize them as related without requiring matching keywords. [S1][S2]

#### Cited sources

##### [S1] Embeddings

**Heading:** (none)

**Chunk ID:** `wordpress:glossary:2385:chunk:v1:d464f828b83a0321c8feb322073de1c3d4834cacba078308071454a17ca41f7c`

**Retrieval score:** `0.894531`

**Source text:**

Embeddings are numerical representations of text or other content like images or audio  that capture meaning in a form a machine can process and compare. When text is converted into an embedding, it becomes a series of numbers that position that text in a high-dimensional space. Content that is semantically similar ends up positioned close together in that space, even if the words used are completely different.

This is what allows an AI system to understand that “how do I reset my password” and “I can’t log in” are related questions without the two phrases sharing any words. The meaning is encoded in the numbers, not the text itself.

Embeddings are foundational to how many AI search and retrieval systems work, including RAG architectures. Rather than searching for exact keyword matches, these systems compare embeddings to find content that is conceptually relevant to a query.

##### [S2] Understanding RAG and Retrieval-Based AI Systems

**Heading:** Retrieval Systems Exist on a Spectrum > Semantic Retrieval

**Chunk ID:** `wordpress:page:2360:chunk:v1:b90f652c226c752907ddc7fc2bda647a957aabfef2871ff7c57150e400be2400`

**Retrieval score:** `0.812500`

**Source text:**

Semantic retrieval uses embeddings and vector search to retrieve content based more on meaning and conceptual similarity than exact wording. In vector search, content and user queries are converted into numerical representations called vectors, which allow the system to compare how closely meanings relate even when the exact words differ.

Instead of only matching words directly, semantic retrieval attempts to identify content that is conceptually related to the query.

Semantic retrieval can improve:

- natural-language querying
- paraphrase handling
- conceptual discovery
- retrieval across terminology differences

For example, a user searching for “ Why does the app keep logging me out? ” may still retrieve documentation discussing:

- session expiration
- authentication timeouts
- login renewal
- expired credentials

even if those exact words do not appear in the query. That flexibility is useful. But it also introduces new problems.

Semantic retrieval is typically:

- less deterministic
- harder to explain
- more difficult to debug
- more vulnerable to retrieving semantically similar but incorrect information

In other words, the system may retrieve content that sounds related without actually being correct in context. That risk becomes more important quickly once generation layers are added on top.

#### Retrieved context

1. **Embeddings** — `0.894531`
   - Heading: (none)
   - Chunk: `wordpress:glossary:2385:chunk:v1:d464f828b83a0321c8feb322073de1c3d4834cacba078308071454a17ca41f7c`

2. **Understanding RAG and Retrieval-Based AI Systems** — `0.812500`
   - Heading: Retrieval Systems Exist on a Spectrum > Semantic Retrieval
   - Chunk: `wordpress:page:2360:chunk:v1:b90f652c226c752907ddc7fc2bda647a957aabfef2871ff7c57150e400be2400`

3. **How RAG Works in Retrieval-Based AI Systems** — `0.808594`
   - Heading: Phase 2: Retrieval — Searching the Knowledge Environment > Step 7: Query Embedding
   - Chunk: `wordpress:page:2366:chunk:v1:5e62c38f1e45a880828f86c8efe27e3882fdeae298a59e3810b7fbb6499c8ff5`

4. **How RAG Works in Retrieval-Based AI Systems** — `0.750000`
   - Heading: Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 4: Embeddings
   - Chunk: `wordpress:page:2366:chunk:v1:e608885ce1731409468b9d616ddc59062c0f90a8528615449f0a5d5202fe80e2`

5. **Semantic Search** — `0.679688`
   - Heading: Common Confusion
   - Chunk: `wordpress:glossary:2402:chunk:v1:4e644f28ab37693d66458e865870f423796f43604e69804cf009116baa008469`

**Dataset note:** Purpose-built source-first case. The gold source was selected before running retrieval.

---

### multi-section-001 — PASS

**Category:** `multi_section`

**Query:** How can lost context during chunking, weak source authority, and missing metadata each cause retrieval failures?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Lost context during chunking can separate information from the surrounding details needed to interpret it correctly, making the resulting chunks harder to retrieve accurately.
- Weak source authority signals can allow a less appropriate source to appear more relevant than the source that should answer the query.
- Missing or inconsistent metadata removes useful signals that retrieval can use to distinguish, filter, or select the right content.

#### Generated answer

- **Lost context during chunking:** Because systems retrieve fragments rather than whole pages, a chunk can be separated from its title, prerequisites, warnings, or preceding steps. It may match the query but lack the product name, required condition, limit, or action needed for a correct answer, so retrieval quality suffers. [S1][S2]
- **Weak source authority:** If authority signals are poor, the system may select the wrong source—for example, ranking an outdated page above current or canonical guidance—rather than the most trustworthy information. [S3][S4]
- **Missing metadata:** Without metadata identifying factors such as product, version, audience, and status, the pipeline cannot reliably distinguish applicable, current content from irrelevant or obsolete material, causing the wrong information to reach the user. [S3]

#### Cited sources

##### [S1] How RAG Works in Retrieval-Based AI Systems

**Heading:** Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 3: Chunking

**Chunk ID:** `wordpress:page:2366:chunk:v1:a04b7e1517199858a707d7ce3829a7d00ba32e29593f8bd9a3bb3a51002f9022`

**Retrieval score:** `0.714844`

**Source text:**

Chunking is one of the most important and misunderstood parts of retrieval systems. Large documents usually aren’t retrieved as complete pages. Instead, they’re split into smaller pieces called chunks, and those chunks become the actual retrieval unit. This is one of the biggest conceptual shifts for documentation teams.

Users increasingly encounter fragments of documentation rather than navigating through full pages in sequence.

A chunk might contain:

- a short procedure
- a troubleshooting section
- a warning block
- a code example
- a conceptual explanation
- a subsection under an H2 or H3 heading

The chunking strategy matters because retrieval systems depend heavily on standalone comprehension. If a chunk loses too much context when separated from the surrounding page, retrieval quality suffers. This is also one of the places where human structural judgment matters most because the system itself cannot reliably determine where conceptual boundaries should begin or end. Retrieval-aware systems may automate the splitting process, but humans still shape the structure the system depends on through headings, hierarchy, layout decisions, and content organization.

This is why retrieval-aware systems often use heading-aware chunking or semantic chunking rather than splitting content arbitrarily every few hundred words.

The system is trying to preserve meaningful conceptual boundaries: a procedure should usually stay attached to its prerequisites; a warning should probably remain attached to the steps it warns about; and a table should ideally remain connected to the explanation that interprets it.

Weak chunking creates retrieval failures that look like AI failures. But the problem may have started much earlier.

##### [S2] When and Why AI Retrieval Fails

**Heading:** Reason 1: The Content Is Too Hard to Interpret

**Chunk ID:** `wordpress:page:2374:chunk:v1:1fd0d122c85f543f202641b2c13dbe68eea1edd29fed0ba6e6cca9b671257731`

**Retrieval score:** `0.628906`

**Source text:**

Retrieval usually works with chunks rather than full pages. A paragraph that makes sense in context may become vague after it’s separated from the title, preceding steps, navigation path, screenshot, or nearby warning.

A reader can resolve references such as “this setting” by looking around the page. A retrieved passage has no such guarantee. It may match the query and still omit the product name, prerequisite, limit, or action the answer depends on.

##### [S3] When and Why AI Retrieval Fails

**Heading:** (none)

**Chunk ID:** `wordpress:page:2374:chunk:v1:eab607338adf6d8e89e78a2fb2ba4a8fb80b7c99940f2fbf2beed3ba4c71f919`

**Retrieval score:** `0.812500`

**Source text:**

A retrieval system can return a weak answer even when the knowledge base contains the right information. The failure often happens earlier in the pipeline: the system retrieves the wrong source, ranks an outdated page too highly, loses context during chunking, or produces an answer that the cited material doesn’t support.

Retrieval quality depends on more than the model and search configuration. Content structure, metadata, permissions, source authority, and maintenance all affect which information reaches the user.

When results fail, examine the signals available to the retrieval pipeline. Did the content identify its product, version, audience, and status? Could the system distinguish a canonical procedure from an old workaround? Did the retrieved passage contain enough context to stand on its own?

##### [S4] When and Why AI Retrieval Fails

**Heading:** Retrieval Failures Expose Weaknesses in the Knowledge System

**Chunk ID:** `wordpress:page:2374:chunk:v1:3ff1ddddb773b8bba1a91acc828eaff2b6f99538b5631e42c93c66241e555272`

**Retrieval score:** `0.738281`

**Source text:**

Outdated pages outranking current documentation point to weak lifecycle controls. The wrong source winning suggests poor authority signals. Answers that lose crucial context expose problems with chunk boundaries or content structure, while restricted material appearing indicates gaps in permission enforcement.

These failures give documentation teams evidence about where the knowledge environment needs work. Technical writers may not own the index, reranker, connectors, or access controls, but they shape source structure, metadata, lifecycle status, canonical guidance, and the documentation that explains how the retrieval system behaves.

Improving those conditions makes search and generated answers more reliable, and gives teams a clearer path for diagnosing the next failure.

#### Retrieved context

1. **When and Why AI Retrieval Fails** — `0.812500`
   - Heading: (none)
   - Chunk: `wordpress:page:2374:chunk:v1:eab607338adf6d8e89e78a2fb2ba4a8fb80b7c99940f2fbf2beed3ba4c71f919`

2. **When and Why AI Retrieval Fails** — `0.738281`
   - Heading: Retrieval Failures Expose Weaknesses in the Knowledge System
   - Chunk: `wordpress:page:2374:chunk:v1:3ff1ddddb773b8bba1a91acc828eaff2b6f99538b5631e42c93c66241e555272`

3. **How RAG Works in Retrieval-Based AI Systems** — `0.714844`
   - Heading: Phase 1: Ingestion — Building the Searchable Knowledge Environment > Step 3: Chunking
   - Chunk: `wordpress:page:2366:chunk:v1:a04b7e1517199858a707d7ce3829a7d00ba32e29593f8bd9a3bb3a51002f9022`

4. **How RAG Works in Retrieval-Based AI Systems** — `0.660156`
   - Heading: Takeaways
   - Chunk: `wordpress:page:2366:chunk:v1:aef986c42ad2012660f687300872c5b2ed79d78d9618ecf69297b39d6c0d788b`

5. **When and Why AI Retrieval Fails** — `0.628906`
   - Heading: Reason 1: The Content Is Too Hard to Interpret
   - Chunk: `wordpress:page:2374:chunk:v1:1fd0d122c85f543f202641b2c13dbe68eea1edd29fed0ba6e6cca9b671257731`

**Dataset note:** Purpose-built source-first case requiring relevant information from multiple sections. Gold sources were selected before running retrieval.

---

### updated-content-001 — PASS

**Category:** `updated_content`

**Query:** How does documentation engineering connect the architecture and operations layers of a knowledge system?

**Expected sufficient evidence:** `true`

**Actual sufficient evidence:** `true`

**Sufficiency correct:** `true`

**Citation behavior correct:** `true`

**Primary citation present:** `true`

#### Required points for qualitative review

- Documentation engineering spans both the architecture layer, where the documentation system is designed, and the operations layer, where that design is implemented and run.
- It connects the two through a feedback loop: architectural decisions shape workflows and infrastructure, while operational experience and constraints feed back into how the system is designed.

#### Generated answer

Documentation engineering bridges the layers by owning both the design of the knowledge system and the tooling, integrations, and automation that implement and enforce that design. This prevents implementation defaults from quietly changing the intended architecture. [S1]

It also maintains a continuous feedback loop rather than a one-time handoff: architecture directs operations; operational data and problems—such as unsuccessful searches or inadequate retrieval—inform changes to the architecture; and those changes update the machinery. [S2]

#### Cited sources

##### [S1] Documentation Engineering

**Heading:** What the Discipline Spans

**Chunk ID:** `wordpress:page:2672:chunk:v1:87abbcd779d51ab1efff333a0143c52e07404387664727ce45cd1bc51db7cbf7`

**Retrieval score:** `0.942292`

**Source text:**

Documentation engineering is defined less by a fixed list of tasks than by what it spans. It sits across the boundary between the two layers of the knowledge infrastructure, and the spanning is the point.

On one side is the architectural layer, the design of how the knowledge system should work and what governs it. That covers:

- documentation strategy and how it aligns with what the product is trying to do;
- the audiences, journeys, and boundaries of the content;
- information architecture, taxonomy, metadata, and content models; governance , ownership, standards, and definitions of done;
- style, terminology, and reusable patterns; the requirements for search, retrieval, AI-readiness, and analytics;
- and the principles for versioning, localization, and the content lifecycle.

It’s the work of deciding what the system should be.

On the other side is the operations infrastructure , the machinery that turns those decisions into a working system. Designing, configuring, building, integrating, and automating the tooling so it enforces the architecture instead of drifting from it. The documentation engineer’s relationship to it is specific: they make sure it embodies the design rather than quietly replacing it with whatever the tools default to.

The role is the spanning itself. A pure strategist who hands a design to someone else to build loses control of it at the exact point where implementation choices silently rewrite the design. A pure toolsmith who automates without owning the design builds a fast, well-run system with no particular reason to be shaped the way it is. Documentation engineering is the job that holds both ends: designing the architecture, then making the machinery carry it out.

##### [S2] Documentation Engineering

**Heading:** What the Discipline Spans > The Feedback Loop Between Architecture and Operations

**Chunk ID:** `wordpress:page:2672:chunk:v1:a63c2a32f851e2ba05d46e1c6444e8d44e31b96857c35ddc42017798e77460c3`

**Retrieval score:** `0.883982`

**Source text:**

What keeps the two ends connected is a loop rather than a handoff. The architecture defines how the operations infrastructure should behave. The infrastructure, once it’s running, produces data and surfaces problems the design didn’t anticipate: content that’s searched for and never found, audiences the model didn’t account for, retrieval that returns fragments instead of answers.

That evidence feeds back into the architecture, which adjusts, which changes what the machinery does next. Keeping that loop turning is one of the discipline’s central jobs. It’s the same loop the downstream knowledge the series described is supposed to travel, and most organizations have the signal and no loop to carry it home. Building the loop is architectural work.

#### Retrieved context

1. **The Knowledge Infrastructure** — `0.952862`
   - Heading: Documentation Engineering Spans Architecture and Operations Layers
   - Chunk: `wordpress:page:2647:chunk:v1:d6663229376cac5076072c319c3116d3af5f183913fac54e63db3efb3472cfd1`

2. **Documentation Engineering** — `0.942292`
   - Heading: What the Discipline Spans
   - Chunk: `wordpress:page:2672:chunk:v1:87abbcd779d51ab1efff333a0143c52e07404387664727ce45cd1bc51db7cbf7`

3. **Documentation Engineering** — `0.942136`
   - Heading: What the Discipline Spans
   - Chunk: `wordpress:page:2672:chunk:v1:49ec96efb031a85bcd9176a8ee83effaf23d5de887ab5ab30e1d011da77e5474`

4. **Documentation Engineering** — `0.892576`
   - Heading: Takeaways
   - Chunk: `wordpress:page:2672:chunk:v1:e6900d03c9efe2af2bcf4421adc390cc2f01e2ff036c3166146014d5b9e77f0d`

5. **Documentation Engineering** — `0.883982`
   - Heading: What the Discipline Spans > The Feedback Loop Between Architecture and Operations
   - Chunk: `wordpress:page:2672:chunk:v1:a63c2a32f851e2ba05d46e1c6444e8d44e31b96857c35ddc42017798e77460c3`

**Dataset note:** Purpose-built source-first case targeting currently indexed content from a revised source document.

---
