# Author documentation page

Use this prompt to create or substantially update a documentation page for the
Python RAG Service.

Use the metadata supplied with the authoring request. Derive only metadata that the selected template explicitly determines, such as `content_type` and `subtitle`. Do not invent missing metadata. `last_modified` is generated automatically.

Before writing:

1. Read the project style guide at `doc-infrastructure/style-guide.md`.
2. Read the content-type template specified in the request.
3. Read the Fern/platform rules at `doc-infrastructure/fern-platform-rules.md`.
4. Review the product sources provided in the request.
5. Use the project's approved terminology at `doc-infrastructure/terminology.md`.

When writing:

* Follow the selected page template, including its required metadata and semantic structure.
* Write for the page's intended audience and user goal.
* Include enough technical detail for the reader to complete the goal without guessing.
* Use simple, clear language without removing necessary technical detail.
* Use the project's warm, relaxed, crisp, and clear voice.
* Describe actual system and component behavior rather than vague AI behavior.
* Add enough local context for sections to remain understandable when retrieved independently, but do not make the page repetitive or unnatural for human readers.
* Prefer canonical documentation over duplicating information that another page owns.
* Do not invent product behavior, configuration, requirements, or examples that are not supported by the source material.

Do not spend time manually reproducing checks handled by the documentation validators or Vale (src/rag_service/commands/documentation). The generated page will be run through those tools separately.

Return a complete MDX page ready for validation.

## Source formatting

Wrap prose in the MDX source at approximately 150 characters per line so the
file is readable without horizontal scrolling.

Do not force-wrap code blocks, tables, URLs, or other content that cannot be
wrapped cleanly.

## Inputs

The authoring request should provide:

- `id`
- title
- content-type template
- description
- page goal or user goal
- `topics`
- `components`, when applicable
- `prerequisites`, when applicable
- `next_steps`, when applicable
- `related_pages`, when applicable
- `lifecycle_status`
- relevant product/source material
- any type-specific metadata that cannot be derived from an authoritative source