---
version: 1
---

# Style Guide

## Voice and Tone

### Voice

Use a warm, relaxed voice that feels natural and approachable without becoming casual or chatty.

Keep the writing crisp and clear. Write like a knowledgeable person helping another technically capable person, not like formal product copy, academic writing, or marketing.

Warmth should come from clarity, helpfulness, and natural language rather than conversational filler, forced friendliness, or humor.

### Direct and plain language

Write directly and use plain language.

Prefer short, concrete sentences over abstract or complicated wording. Use familiar words when they are accurate, and avoid filler, buzzwords, and unnecessary qualifiers.

Be specific about what the reader should do, what the system does, and what result to expect.

Prefer:

* The service returns no results when it can’t find sufficiently relevant content.

Over:

* The service may, under certain circumstances, determine that no sufficiently relevant content is available for return.

Do not simplify language so much that technical meaning becomes less precise.

### Contractions

Use common contractions, such as it’s, you’re, that's, and don’t, to create a friendly, informal tone.

Don't mix contractions and their spelled-out equivalents in UI text. For example, don’t use can’t and cannot in the same UI.

Never form a contraction from a noun and a verb, such as "Microsoft’s developing a lot of new cloud services".

Avoid ambiguous or awkward contractions, such as there’d, it’ll, and they’d.

### Technical Depth

Write at the level of technical detail the reader needs to complete their goal without guessing.

Use simple, clear language even when explaining technical concepts. Prefer precise terms over vague wording, but avoid jargon when a simpler term works just as well. When specialized terminology is necessary, use the correct term and explain it briefly when the audience may not already know it.

Do not remove important technical detail just to make the documentation easier to read. Simplify the language, not the information.

### Explaining technical concepts

Assume readers are technically capable, but do not assume they already know this project's architecture, retrieval approach, or terminology.

Explain specialized concepts when understanding them is necessary to complete the task or understand the system. Keep explanations brief and place them close to where the concept is first needed.

Do not explain common developer concepts unless the explanation is necessary for the task. Avoid interrupting procedures with background information that the reader does not need to continue.

For unfamiliar or project-specific terms, use the correct term rather than replacing it with vague language, and explain it in plain language when needed.

## Audience focus

Every documentation page declares one or more intended audience groups in the
`audience` frontmatter field. Either `primary`, `secondary`, or both.

Do not add background information only to make a page useful to every possible audience. Keep each page focused on its purpose, and link to supporting explanation when deeper context is useful. 

Write each page for the reader most likely to use it.

A page can target both audiences when its purpose is useful to both groups.

### Primary

Developers integrating with or deploying the Python RAG Service.

Primary-audience documentation should prioritize the information needed to install,
configure, index content, use the API, and integrate the service into an application.

### Secondary

Developers and documentation engineers who want to understand, evaluate, or extend
the Python RAG Service.

Secondary-audience documentation can include deeper architectural, retrieval,
evaluation, and implementation context.

## AI and system behavior language

### Describe actual system behavior

Describe what the system, component, or model actually does.

Name the responsible component when that distinction matters. Prefer specific descriptions such as **the retrieval pipeline retrieves**, **the model generates**, or **the application validates** over vague phrases such as **the AI knows**, **the AI decides**, or **the system understands**.

Do not imply that a language model performs checks or guarantees that are actually handled by application logic. For example, the model may propose citations, but the application validates them before returning the answer.

Use human-like language only when it is a harmless shorthand and does not misrepresent how the system works.

Prefer:

* The retrieval pipeline determines whether any results meet the support requirements.  
* The model generates an answer from the supplied context.  
* The application validates the model's proposed citations.

Avoid:

* The AI knows whether the documentation can answer the question.  
* The model verifies its sources.  
* The system understands that the query is unsupported.

### Claims about certainty and guarantees

Use absolute language only when the behavior is actually guaranteed by the implementation.

Avoid words such as **always**, **never**, **ensures**, **guarantees**, and **prevents** unless the system enforces that behavior in all supported cases.

When behavior depends on retrieval quality, model output, configuration, or external services, describe the condition or limitation instead of overstating certainty.

Prefer:

* The application validates citations before returning them.  
* The model is instructed to answer only from the supplied context.  
* The support gate can return no relevant results when the retrieved content does not adequately support the query.

Avoid:

* The model always answers from the documentation.  
* Citation validation prevents hallucinations.  
* Hybrid retrieval guarantees relevant results.

Distinguish between **design intent**, **implemented checks**, and **guaranteed behavior**. Do not present an instruction to the model as a guarantee that the model will follow it.

## Headings and semantic structure

### Descriptive headings

Use headings that clearly describe the subject or action in the section.

Prefer specific headings such as **Configure Qdrant**, **Handle insufficient evidence**, or **Run the retrieval evaluation** over vague headings such as **Details**, **More information**, or **Configuration**.

Structure sections around one coherent idea, task, or concept. If a section covers several distinct subjects, split it into smaller sections with meaningful headings.

Keep the heading close to the content it describes so the section remains understandable if it is retrieved or viewed separately from the rest of the page.

Follow the standard section structure defined for the page's content type. Use consistent labels such as **Prerequisites**, **Next steps**, and **Related pages** when those sections have the same meaning across pages.

Use heading levels to show hierarchy. Do not skip levels or use headings only for visual styling.

Avoid headings that depend on surrounding context to make sense.

Prefer:

* Configure the embedding provider  
* How citation validation works  
* Handle an empty search response

Avoid:

* Configuration  
* How it works  
* Other considerations

### Local context within sections

Write sections so they are understandable when read or retrieved on their own, without making the page repetitive or unnatural for human readers.

Add local context when the subject would otherwise be unclear. Name the object, endpoint, setting, or process when necessary, but do not repeat information that is already obvious from the heading or nearby content.

Use pronouns and shortened references naturally when their meaning is clear. Avoid vague references such as **this**, **it**, or **the process** only when the reader would need missing context to understand what they refer to.

Keep conditions, warnings, and exceptions close to the instruction or behavior they qualify.

Keep examples with the explanation or scenario they support. Do not separate an example from information needed to understand when or why to use it.

Avoid very large sections that combine unrelated ideas, but do not split content into artificially small sections solely to improve retrieval.

Prioritize clear, natural documentation for human readers. Add only the context needed to help a section retain its meaning when retrieved separately.

A useful test is:

* If this section were retrieved without the rest of the page, would its main subject still be clear without adding unnecessary repetition?

## Cross-references and duplication

Link to the canonical page when information is already explained elsewhere instead of repeating the full explanation.

Keep repeated information brief and limited to the context the reader needs to continue. Do not make readers leave the page for every small detail, but avoid maintaining the same instructions, definitions, or behavior descriptions in multiple places.

Use descriptive link text that tells the reader what they will find.

Prefer:

* See Configure the service for all supported environment variables.  
* For the complete error schema, see Errors.

Avoid:

* See here for more information.  
* Click this link.

Avoid location-dependent references such as **above**, **below**, or **in the previous section** when a direct reference to the page, section, or concept would be clearer and more durable.

When the same concept must appear in more than one place, keep one location authoritative and make the repeated version clearly secondary.

Do not duplicate API behavior, configuration details, or other factual system information across multiple pages when one page already serves as the source of truth.

## Terminology governance

Use one preferred term for each project-specific concept and apply it consistently across the documentation.

Use [Terminology](terminology.md) to define terminology choices and distinctions, such as which term is preferred, which alternatives to avoid, and when similar terms have different meanings.

Use the **glossary** to explain what important technical and project-specific terms mean for readers.

Use **Vale** to enforce selected terminology rules automatically, such as preferred spellings, prohibited variants, and approved replacements.

For example:

* Terminology: Use **reranking**, not **re-ranking**.  
* Glossary: Define what **reranking** means.  
* Vale: Flag **re-ranking** and suggest **reranking**.

Add a terminology rule when inconsistent wording could make the documentation less clear, technically inaccurate, or harder to maintain.

Add a glossary term when readers are likely to need a definition to understand the documentation.

Do not add every technical word to the terminology reference or glossary. Common industry terms do not need project-specific rules unless this project uses them in a particular way.

When a new preferred term is needed, define the terminology decision first, then update the glossary and Vale rules where appropriate.
