---
name: author-doc-page
description: >
  Author new Python RAG Service documentation pages in fern/docs/pages,
  including pages already initialized using create_doc_page. Use when
  asked to outline, draft, refine, or finalize a new documentation page.
  Do not use for updating existing authored documentation.
---

# Author Documentation Page

Create new documentation pages using the project's content model, templates, documentation standards, and authoritative sources.

Work collaboratively with the user through four steps: outline, draft, final draft, and metadata finalization.

## General instructions

- Use the Documentation map in `AGENTS.md` to locate documentation
  resources and authoritative sources.
- Consult the project standards and references specified in each step.
- Verify technical claims against authoritative sources. Flag missing
  or conflicting evidence rather than inventing details.
- Follow the four steps in order and obtain user approval at each
  approval checkpoint.
- Preserve approved decisions unless new evidence or user feedback
  requires revisiting them.
- Maintain `lifecycle_status: draft` through Step 3. After Step 3
  approval, set it to `review`. After Step 4 approval, set it to
  `published` and run production validation.
- Do not commit or push changes unless explicitly requested.

## Step 1: Write the outline

Create a section-by-section outline for a new documentation page or previously initialized documentation page (with frontmatter only)
in `fern/docs/pages/`.

### Required user input

- **Page information:** `id`, `title`, `description`, and `content_type`,
  or the path to a page already created using `create_doc_page`.
- **Prerequisites (if applicable):** Page IDs from
  `doc-infrastructure/page-registry.yml` identifying documentation
  the reader needs before successfully using the new page.
- **Page summary:** What the page should cover, expanding on the
  frontmatter `description`.
- **Context sources:** Relevant source code, specifications, existing
  documentation, or other authoritative references.

If a page path is provided, read its existing frontmatter.

Ask for clarification if essential information is missing or unclear.

### Review project context

1. Use the Documentation map in `AGENTS.md` to locate relevant
   authoritative sources.
2. Read `doc-infrastructure/content-model.yml` for metadata
   requirements and selection guidance.
3. Review the template associated with the selected `content_type`
   in `doc-infrastructure/templates/`.
4. Review relevant existing documentation to establish context
   and avoid duplicating content.
5. Read the prerequisite pages, if provided, to establish what
   the reader is expected to know or have completed. If no
   prerequisites are provided, identify any direct dependencies
   using the relationship selection rules in `content-model.yml`.

### Select initial metadata

Recommend missing metadata values and review existing values
against the page's intended purpose, audience, and scope.

- Propose a `subtitle` if one has not been provided.
- Refine the `description` when appropriate.
- Select `audience`, `topics`, and `components` using the
  `description` and `use_when` guidance in `content-model.yml`.
- Select the most specific relevant topics. Include parent topics
  only when the page substantially covers the broader subject.
- Select components the page meaningfully describes, configures,
  operates, evaluates, or integrates with.
- Do not assign metadata values based solely on passing references.

Use only approved controlled values. Treat selections as provisional until Step 4.

### Create the outline

Create an outline that:

- Follows the selected content-type template.
- Uses descriptive headings and briefly identifies what each
  section will cover.
- Identifies planned procedures, examples, code samples, and
  supporting material where relevant.
- Identifies missing evidence, unresolved questions, and technical
  details requiring verification.
- Account for the reader's prerequisite knowledge and completed
  tasks without unnecessarily repeating prerequisite content.

Keep the outline focused on the page's purpose. Do not write the full content during this step.

### Review and prepare the page

Present the outline, proposed metadata, recommended changes to existing metadata, and unresolved questions for user approval.

After approval:

- If the page does not exist, run `create_doc_page` with the
  approved metadata.
- If the page already exists, confirm that it was initialized
  for authoring and has `lifecycle_status: draft`. Preserve its
  ID and file path.

For either starting point:

1. Populate or update frontmatter with approved metadata.
2. Confirm that `lifecycle_status` is `draft`.
3. Populate or regenerate `last_modified` using the documented
   command in `doc-infrastructure/README.md`.
4. Confirm that the page is registered in
   `doc-infrastructure/page-registry.yml`.
5. Add the approved outline using the selected template.

Do not rerun `create_doc_page` for an existing page.

Populate `prerequisites` with approved page IDs, if applicable. Leave `next_steps` and `related_pages` for Step 4.

**Stop after preparing the page.** Wait for the user to request
Step 2: Create the draft.

## Step 2: Create the draft

Expand the approved outline into a complete draft in the existing MDX
file. Focus on technical accuracy, completeness, and appropriate technical depth.

### Review project context

Before drafting:

1. Read `doc-infrastructure/technical-accuracy-rules.md`.
2. Read `doc-infrastructure/fern-platform-rules.md`.
3. Read `doc-infrastructure/terminology.md`.
4. Review the authoritative context sources identified in Step 1. Consult additional sources when necessary to verify implementation details.
5. Review relevant existing documentation to maintain consistency and avoid duplicating content.

Use the Documentation map in `AGENTS.md` to locate additional sources of truth when needed.

### Write the draft

- Follow the approved outline and content-type template.
- Apply the technical accuracy, terminology, and Fern platform rules.
- Explain concepts, procedures, and system behavior at the level
  of detail appropriate for the intended audience.
- Include procedures, examples, commands, and expected results
  where appropriate.
- Link to existing documentation when a subject is already covered
  in detail elsewhere.

Do not invent commands, configuration options, API behavior, implementation details, or example output.

### Verify technical accuracy

Apply the verification requirements in `technical-accuracy-rules.md`, using a level of verification appropriate to each claim.

For example:

- **API details and configuration:** Verify parameters, defaults, endpoints, and behavior against the implementation or authoritative specifications.
- **Commands and code examples:** Check syntax and dependencies. Run safe examples when an appropriate environment is available.
- **Evaluation results:** Verify metrics, dataset versions, and findings against recorded evaluation reports.
- **System behavior:** Confirm implementation-specific claims against the relevant code, tests, or configuration.
- **General technical explanations:** Use reliable technical knowledge and consult authoritative sources when details are uncertain or specific to this project.

Do not repeat verification unnecessarily when reliable evidence has already been established.

If information cannot be verified, record the specific question or gap rather than filling it with assumptions.

### Review the draft

Present the completed draft for user review, identifying:

- Unverified claims or examples.
- Missing information and unresolved questions.
- Significant deviations from the approved outline.

Keep `lifecycle_status: draft`.

Reserve the full editorial review, including voice, tone, and AI-generated content fingerprints, for Step 3.

**Stop and wait for user approval before proceeding to Step 3: Create the final draft.**

## Step 3: Create the final draft

Refine the approved draft for clarity, readability, consistency,
and editorial quality while preserving technical accuracy and
the intended meaning.

### Review project standards

1. Read `doc-infrastructure/style-guide.md`.
2. Read `doc-infrastructure/terminology.md`.
3. Refer to `doc-infrastructure/technical-accuracy-rules.md`
   when editing technical explanations or resolving accuracy concerns.

Apply all applicable style guide rules throughout the editorial
review, including those not explicitly referenced in the passes.

### Edit the draft

Complete the following editorial passes in order. Revisit earlier
decisions when necessary.

#### Pass 1: Review structure and flow

- Confirm that the page follows the approved outline and
  content-type template.
- Review section order, headings, hierarchy, and coherence.
- Identify missing, misplaced, duplicated, or unnecessary content.
- Ensure sections contain enough context to remain understandable
  when retrieved independently.
- Apply the style guide's Cross-references and duplication rules,
  including positional cross-references.
- Review existing diagrams and determine whether additional
  visualizations would improve understanding, following the
  style guide's Diagrams and visualizations guidance.

Flag substantial changes to the approved scope for user review.

#### Pass 2: Edit for clarity and conciseness

Apply the style guide's plain language, readability, and Audience
focus rules.

Remove unnecessary complexity, filler, repetition, and vague
language without sacrificing technical detail or meaningful
conditions and limitations.

Ensure explanations, procedures, and examples provide sufficient
information for the intended audience.

#### Pass 3: Apply voice and tone

Apply the Voice and Tone rules in `style-guide.md`.

#### Pass 4: Review terminology and acronyms

Apply the rules in `terminology.md` and the Acronyms section
of `style-guide.md`.

Check preferred terminology, distinctions between related
concepts, acronym usage, and consistency. Identify terminology
gaps or conflicts requiring user input.

#### Pass 5: Remove AI-generated content fingerprints

Review the complete page against **Avoid AI-generated content
fingerprints** in `style-guide.md`.

Apply the section's **Use judgment** guidance. Do not remove
useful language solely because it resembles a listed pattern.

#### Pass 6: Perform a final accuracy and consistency check

- Confirm that editorial changes have preserved technical meaning.
- Recheck substantially rewritten claims and verify newly
  introduced technical information and examples.
- Resolve outstanding accuracy questions from Step 2 where possible.
- Confirm that conditions, limitations, warnings, and expected
  outcomes remain accurate.
- Check for unintended repetition or inconsistency introduced
  during editing.
- Do not automatically rewrite technically accurate content solely
to satisfy a stylistic suggestion when doing so would reduce
clarity or precision.
- Confirm that the completed page follows all applicable rules
  in `style-guide.md`, including those not explicitly addressed
  in earlier passes.

Do not repeat verification completed in Step 2 unless information
has changed or new uncertainty has been introduced.

Record unresolved issues for user review.

### Run documentation checks

Run the regular documentation validation command documented in
`doc-infrastructure/README.md`.

Resolve issues introduced by your changes. Report remaining
failures and checks that could not be completed.

### Review the final draft

Present the revised page for user review, summarizing:

- Significant editorial changes.
- Remaining technical questions or unresolved issues.
- Validation results.

Keep `lifecycle_status: draft` until the user approves the final
draft, then set it to `review`.

**Stop and wait for the user to request Step 4: Finalize metadata
and page relationships.**

## Step 4: Finalize metadata and page relationships

Finalize the approved page's metadata, relationships, and navigation.

### Review metadata

1. Read `doc-infrastructure/content-model.yml`, including its selection guidance.
2. Review the existing `audience`, `topics`, and `components` against the completed page. Recommend additions or changes where appropriate.
3. Review the `description` and `subtitle` for accuracy and clarity.
4. Preserve the page's `id` and `content_type` unless a change is approved.
5. Reassess the prerequisites established in Step 1 against the completed page. Add, remove, or change them as appropriate.

Use only approved controlled values. Base metadata decisions on substantive content, not passing references.

### Finalize page relationships

1. Read the `page_relationships` definitions and selection rules in `content-model.yml`.
2. Review `fern/docs.yml` to understand the documentation structure and discover candidate pages.
3. Use `doc-infrastructure/page-registry.yml` to identify registered page IDs.
4. Examine relevant existing pages to evaluate their content, purpose, and relationship to the current page.

Consider candidates across the documentation set, not just within the same navigation section.

For each candidate:

- Determine how it supports the current page.
- Classify it as a prerequisite, next step, or related page using the content model.
- Prefer direct, useful connections over broadly related pages.
- Exclude weak, redundant, or merely topic-related recommendations.

Present the proposed relationships with each page's title, ID, relationship type, and a brief justification. Prefer a small, curated set.

Identify existing pages that would benefit from linking to the new page. Propose those changes for user approval before modifying existing pages.
Do not automatically create reciprocal relationships.

### Update and validate

After approval of the proposed metadata and relationships:

1. Update the page's frontmatter and add approved relationship links following the template and Fern rules.
2. Apply separately approved changes to existing pages. Apply the relevant style guide rules to any content added or
modified during this step.
3. Add the new page to `fern/docs.yml` if it isn't already included.
4. Regenerate `last_modified` using the command in `doc-infrastructure/README.md`.
5. Run the regular documentation validation command and resolve issues introduced by your changes.

Keep `lifecycle_status: review` until final approval.

### Final approval

Present the completed metadata, relationship and navigation changes, validation results, and any unresolved issues for user approval.

After approval:

1. Set `lifecycle_status: published`.
2. Run production validation using the command in `doc-infrastructure/README.md`.
3. Resolve failures and report the results.

Do not commit or push unless explicitly requested. GitHub Actions handles publishing when changes are pushed to the publishing branch.