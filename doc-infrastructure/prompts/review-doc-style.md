# Review documentation style

Use this prompt to review a Python RAG Service documentation page for project-specific style rules that require editorial judgment.

This review is advisory. Report meaningful style issues, not personal writing preferences.

## Before reviewing

1. Read the project style guide at `doc-infrastructure/style-guide.md`.
2. Read the project terminology guidance at `doc-infrastructure/terminology.md`.
3. Read the documentation page being reviewed.
4. Read the relevant content-type template to understand the page's purpose and expected kind of content.
5. Review the relevant product/source material provided with the review request when needed to assess technical depth, system behavior, or claims.

Do not use this review to repeat checks already handled by Vale or the documentation validators.

## Review scope

Review the page for the following judgment-based rules.

### Voice

Check whether the writing is warm and relaxed, crisp and clear, and natural without becoming chatty, overly formal, promotional, or academic.

Do not suggest wording changes solely because another phrasing is possible.

### Technical depth

Check whether the page gives the intended reader enough technical information to complete the page's goal or understand the subject without unnecessary guessing.

Do not recommend removing necessary technical detail merely to make the writing shorter or simpler.

### Explaining technical concepts

Check whether specialized or project-specific concepts are explained when the intended reader is likely to need the explanation.

Also check for unnecessary explanations of common developer concepts or background material that interrupts the page's purpose.

### Audience focus

Check whether the amount and type of information fit the page's intended audience and goal.

Flag background or detail that appears to serve a different audience at the expense of the page's primary purpose.

### Clarity and directness

Check for wording that is unnecessarily abstract, complicated, indirect, or verbose when a clearer expression would preserve the same technical meaning.

Do not perform general copyediting or report minor wording preferences.

### AI and system behavior

Check whether the writing accurately describes what the model, retrieval pipeline, application, support gate, or other system component does.

Flag vague or human-like descriptions when they obscure or misrepresent the actual behavior, including cases that simple pattern matching would not reliably catch.

### Certainty and guarantees

Check whether claims accurately reflect the level of certainty supported by the implementation.

Distinguish among design intent, model instructions, implemented checks, and guaranteed behavior.

Flag claims that overstate what the system can ensure, prevent, or guarantee.

### Headings and semantic clarity

Check whether headings meaningfully describe their sections in context, including headings that may not be caught by deterministic vague-heading rules.

Check whether sections generally focus on one coherent idea, task, or concept.

Do not review required section presence or heading hierarchy that is already handled by validation.

### Local context

Check whether sections retain enough context to make sense when read or retrieved independently.

At the same time, flag unnecessary repetition or awkward over-contextualization added only to make sections self-contained.

Prioritize natural reading for humans while preserving enough local context for retrieval.

### Cross-page duplication

Flag substantial explanations, instructions, or factual information that appear to duplicate content owned by another canonical page when a short summary and cross-reference would be more appropriate.

Do not flag brief context that helps the reader continue without leaving the page.

## Do not review

Do not report issues that are owned by deterministic tooling, including:

* required or allowed frontmatter fields
* controlled metadata values
* required content-type sections
* relationship integrity
* Fern/platform syntax and rules
* Markdown or MDX syntax
* exact terminology substitutions already enforced by Vale
* known prohibited phrases already enforced by Vale
* product-name first-use checks
* broken links
* OpenAPI consistency checks handled elsewhere

If a deterministic issue happens to be visible, do not include it in this style review.

## Evidence and uncertainty

Base every finding on a documented project style rule.

Do not invent product behavior or missing requirements.

If the supplied source material is not sufficient to judge technical depth, component behavior, or the certainty of a claim, do not guess. State that the specific point could not be assessed from the available sources.

## Findings

Report only meaningful issues that are reasonably likely to improve the page.

For each finding, provide:

* **Rule:** the applicable style-guide rule or category
* **Location:** the heading, paragraph, or short excerpt that identifies where the issue occurs
* **Issue:** what conflicts with the project style guidance
* **Why it matters:** the effect on clarity, accuracy, audience focus, or usability
* **Suggested change:** a concise recommendation or replacement when useful

Do not rewrite the entire page unless explicitly asked.

Do not report sections that already follow the style guide.

If no meaningful issues are found, return:

`Style review passed. No judgment-based style issues found.`

## Inputs

The review request should provide:

* the documentation page to review
* the relevant content-type template
* intended audience
* page or user goal
* relevant product/source material when needed to assess technical depth or system behavior
