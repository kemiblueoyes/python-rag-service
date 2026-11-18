---
version: 1.1
---

# Style Guide

## Voice and Tone

### Voice

Use a warm, relaxed voice that feels natural and approachable without becoming casual or chatty.

Keep the writing crisp and clear. Write like a knowledgeable person helping another technically capable person, not like formal product copy, academic writing, or marketing.

Warmth should come from clarity, helpfulness, and natural language rather than conversational filler, forced friendliness, or humor.

### Direct and plain language

Write directly and use plain language.

Prefer short, concrete sentences over abstract or complicated wording. Use familiar words when they are accurate, and avoid buzzwords.

Be specific about what the reader should do, what the system does, and what result to expect.

Avoid: 

> The service may, under certain circumstances, determine that no sufficiently relevant content is available for return.

Prefer:

> The service returns no results when it can’t find sufficiently relevant content.

Do not simplify language so much that technical meaning becomes less precise.

### Avoid filler and subjective language

Avoid filler words and superfluous adjectives such as 'really nice feature', 'it may be that', 'and that's it'.

Avoid subjective phrases. "You can easily...". "it's simple to...". "It's as easy as that!"

Rather than say how simple it's to do something, show the developer through specific steps. Let the developer be the judge of whether something is simple or not.

### Avoid unnecessary hedging

Use direct, confident language when describing established behavior.

Avoid vague qualifiers such as *might*, *maybe*, *probably*, and *should* when the behavior is known and can be stated precisely.

Keep qualifiers when they communicate genuine uncertainty, conditional behavior, recommendations, or limitations. Do not make a
statement more definite than the implementation supports.

### Active voice

Use active voice. Make the person, command, or component that performs the action the subject of the sentence.

Passive voice hides that actor, so the reader has to infer who prints a message, writes a file, or updates a record. Name the actor in the main action and in any condition that has one.

Avoid:

> The same summary line is printed only after those vector records are upserted. 

and

> The document and chunk files are written only after vector synchronization returns.

Prefer:

> The command prints the same summary line only after it upserts those vector records.  

or

> The command writes the document and chunk files only after vector synchronization returns.

### Use present tense

Use present tense. It's easier to read and translate.

Avoid:

> Command X will start the server.

Prefer:

> Command X starts the server.

### Contractions

Use common contractions, such as it’s, you’re, that's, and don’t, to create a friendly, informal tone.

Don't mix contractions and their spelled-out equivalents in UI text. For example, don’t use can’t and cannot in the same UI.

Never form a contraction from a noun and a verb, such as "Microsoft’s developing a lot of new cloud services".

Avoid ambiguous or awkward contractions, such as there’d, it’ll, and they’d.

### Use second person

You should use 'you' rather than 'we' when referring to the reader, especially in task-based material such as tutorials.

The reason for generally avoiding 'we' is that it can potentially create confusion - who exactly is 'we'? 

It's always best to be explicit: if the developer needs to do something, tell them directly what they need to do and how.

Avoid:

> We now need to enter an API Key.

Prefer:

> You must to enter your API Key in the terminal.

or

> Enter your API Key in the terminal.

### Avoid Latin phrases and abbreviations

Latin abbreviations can occasionally cause confusion if not used correctly. For example, people can get confused between the meaning of "i.e." and "e.g." (and sometimes use them as equivalent).

Examples:

* Use 'for example', instead of 'e.g.'
* Use 'that is' rather than 'i.e.'

Instead of using 'etc.', be specficic.

Avoid:

> The SDK supports common backend languages like Node.js, Python, Ruby, etc.

Prefer:

> The SDK supports Node.js, Python, Ruby, and other popular backend languages.

or

> The SDK supports backend languages like Node.js and Python.

Sometimes writers create variations of Latin abbreviations, such as 'eg', 'e.g', 'eg.' and so on. It's best to avoid this. When automated spell checkers are run, these variations can stop the doc build. 

Avoid Latin phrases such as "quid pro quo", "ad nauseum", "vis-a-vis". They can also be difficult to translate, and not everyone is familiar with their meaning.

### Avoid slang

Avoid slang as this can be hard for some developers to interpret.

For example:

* Don't use overly dramatic words like 'crash' or 'implode', use 'error'.
* Use 'launch' or 'start' rather than 'fire up'.
* Bear in mind the reader's daily language may not be English.
* A mouse is clicked and a keyboard is pressed. Avoid terms such as 'hit' or 'punch' when referring to the keyboard. Avoid: "Now punch in any key to continue."
* Avoid idiomatic language such as "You're good to go", "We'll run this by you", "You're all done".

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

## Headings and semantic structure

### Descriptive headings

Use headings that clearly describe the subject or action in the section.

Prefer specific headings such as **Configure Qdrant**, **Handle insufficient evidence**, or **Run the retrieval evaluation** over vague headings such as **Details**, **More information**, or **Configuration**.

Structure sections around one coherent idea, task, or concept. If a section covers several distinct subjects, split it into smaller sections with meaningful headings.

Keep the heading close to the content it describes so the section remains understandable if it is retrieved or viewed separately from the rest of the page.

Follow the standard section structure defined for the page's content type. Use consistent labels such as **Prerequisites**, **Next steps**, and **Related pages** when those sections have the same meaning across pages.

Use heading levels to show hierarchy. Do not skip levels or use headings only for visual styling.

Avoid headings that depend on surrounding context to make sense, such as:

* Configuration  
* How it works  
* Other considerations

Prefer:

* Configure the embedding provider  
* How citation validation works  
* Handle an empty search response

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

## Acronyms

Define acronyms on first use on a page, in the form of "Oracle Cloud Infrastructure (OCI)". On subsequent use in a topic you don't need to redefine the acronym.

## Cross-references and duplication

Link to the canonical page when information is already explained elsewhere instead of repeating the full explanation.

Keep repeated information brief and limited to the context the reader needs to continue. Do not make readers leave the page for every small detail, but avoid maintaining the same instructions, definitions, or behavior descriptions in multiple places.

Use descriptive link text that tells the reader what they will find.

Avoid:

>  See here for more information.  

and

> Click this link.

Prefer:

> See Configure the service for all supported environment variables.  

or

> For the complete error schema, see Errors.

When the same concept must appear in more than one place, keep one location authoritative and make the repeated version clearly secondary.

Do not duplicate API behavior, configuration details, or other factual system information across multiple pages when one page already serves as the source of truth.

### Positional cross-references

Do not use **above**, **below**, **following**, **next**, or **previous** to point to another place on the same page.

A phrase such as "in the section above," "the checks below," or "the following table" only works while the page stays in that order. Name the heading (and link to it), setting, or concept instead.

Avoid:

* The checks below must succeed.
* See the section above.
* The following table lists each setting.
* The next section explains citation validation.

Prefer:

* Evidence sufficiency and citation validation must both succeed before the API returns a grounded answer.
* See **Citation validation** for the checks the application runs on the proposed answer.

**Next steps** stays the standard heading for that section. This rule applies when **next** points somewhere else on the page, such as "the next section."

## Avoid AI-generated content fingerprints

Write naturally and directly. Avoid formulaic language, exaggerated claims, and repetitive patterns commonly found in AI-generated content.

Apply these rules during editing. Don't sacrifice clarity, accuracy, or natural sentence flow simply to eliminate a particular pattern.

### 1. Remove filler and unnecessary framing

Get to the point. Avoid introductions, transitions, and conclusions that announce or summarize information without adding value.

Common patterns to remove include:

* "Let's explore..." or "Let's dive into..."
* "It's important to note that..."
* "Here's the thing..." or "Here's the catch..."
* "Putting it all together..."
* "In summary..." or "Ultimately..."

Start with useful information. End when the explanation or task is complete.

### 2. Avoid artificial contrasts and inflated claims

Don't use dramatic contrasts to make ordinary observations sound insightful.

Avoid patterns such as:

* "It's not about X. It's about Y."
* "X isn't just A. It's B."
* "The real challenge is..."

State the relationship directly instead.

Use contrast when it explains a meaningful technical distinction, such as the difference between relevance and evidence sufficiency.

### 3. Use concrete language and examples

Name the actual components, actions, and results instead of relying on vague descriptions or generic examples.

Avoid:

> The system intelligently processes information to deliver better results.

Prefer:

> The retrieval pipeline combines vector and BM25 retrieval, then reranks the candidate chunks.

Use examples that demonstrate real behavior relevant to the documentation. Don't introduce hypothetical applications or scenarios unless they help explain the subject.

### 4. Vary sentence structure naturally

Avoid repetitive sentence patterns, excessive short sentences, and mechanical transitions.

Avoid:

> The service retrieves chunks. It ranks them. It filters them. It returns results.

Prefer:

> The retrieval pipeline finds and ranks candidate chunks, applies the support gate, and returns the selected results.

Combine or separate sentences based on clarity and natural rhythm, not a fixed formula.

### 5. Avoid unnecessary formatting

Use formatting to clarify information, not to create artificial structure.

* Don't use em dashes. Restructure the sentence or use appropriate punctuation.
* Avoid repetitive bold-label bullet patterns such as "**Feature:** Description" when ordinary bullets would work.
* Don't divide simple explanations into multiple headings, lists, or callouts without a clear reason.

Keep formatting appropriate to the content type and the information being presented.

### 6. Respect the reader's knowledge

Don't overexplain familiar technical concepts or repeat information to make a page seem more comprehensive.

Assume readers have the technical background described in the page's intended audience. Explain unfamiliar or project-specific concepts when necessary.

Provide enough context to make the documentation useful without interrupting the reader with unnecessary background information.

### Use judgment

These rules identify patterns to review, not phrases to remove automatically in every context.

Sentence fragments, occasional conversational phrasing, and varied sentence lengths are acceptable when they improve readability.

Preserve useful contrasts, explanations, and formatting when they serve a clear purpose. The goal is natural, precise documentation, not rigid compliance with stylistic formulas.
