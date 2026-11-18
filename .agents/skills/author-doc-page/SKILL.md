---
name: author-doc-page
description: >
  Create new Python RAG Service documentation pages through a four-step
  authoring workflow: outline, draft, final draft, and metadata finalization.
  Use when asked to author a new documentation page in fern/docs/pages,
  including tutorials, how-to guides, explanations, overviews, and reference
  pages. Follow the project's content model, documentation templates,
  technical accuracy rules, Fern conventions, and editorial standards.
---

# Author Documentation Page

Create a new documentation page for the Python RAG Service using the project's
content model, documentation standards, and approved source material.

Work collaboratively with the user through four stages, from the initial outline
to a completed, validated page.

## Workflow

1. **Outline:** Create a section-by-section outline using the appropriate
   content-type template and the user's documentation plan.
2. **Draft:** Write the page based on the approved outline, following the
   project's technical accuracy, terminology, and Fern requirements.
3. **Final draft:** Edit for structure, clarity, voice, tone, and style.
   Run documentation checks and obtain approval.
4. **Finalize metadata:** Review controlled metadata, page relationships,
   and navigation. Validate the completed page.

Obtain user approval before proceeding to the next step.

After Step 3 approval, set `lifecycle_status: review`. After Step 4 approval,
set `lifecycle_status: published` and run production validation.

Do not commit or push changes unless explicitly requested.

## Project context

Before starting, review `AGENTS.md`, particularly its Documentation map,
to locate documentation files and authoritative implementation sources.

Use the following files as needed throughout the workflow:

| File | Purpose |
| --- | --- |
| `doc-infrastructure/content-model.yml` | Required metadata, controlled vocabulary, definitions, and selection guidance |
| `doc-infrastructure/templates/` | Page structure based on `content_type` |
| `doc-infrastructure/technical-accuracy-rules.md` | Technical accuracy and verification requirements |
| `doc-infrastructure/terminology.md` | Approved terminology and usage |
| `doc-infrastructure/fern-platform-rules.md` | Fern and MDX authoring requirements |
| `doc-infrastructure/style-guide.md` | Voice, tone, clarity, and editorial standards |
| `doc-infrastructure/README.md` | Documentation commands, validation, and maintenance procedures |
| `doc-infrastructure/page-registry.yml` | Registered page IDs and content types |

Consult each reference at the stage where it's needed. Do not assume that
existing documentation accurately reflects current implementation behavior.

## General instructions

- Follow the four steps in order. Do not skip approval checkpoints.
- Use authoritative sources to establish documented behavior. Flag missing
  or conflicting evidence rather than inventing technical details.
- Use the definitions and `use_when` guidance in `content-model.yml` when
  selecting metadata values.
- Preserve previously approved decisions unless new evidence or user feedback
  requires revisiting them.
- Explain significant recommendations and unresolved questions before
  making changes that depend on user judgment.
- Keep the page's lifecycle status aligned with its current workflow stage.

## Step 1: Write the outline

Create a section-by-section outline for a new documentation page in `fern/docs/pages/`, following the template associated with its `content_type` in `doc-infrastructure/templates/`.

### Required user input

- **Page information:** `id`, `title`, `description`, and `content_type`.
- **Page summary:** What the page should cover, expanding on the frontmatter `description`.
- **Context sources:** Relevant source code, specifications, existing documentation, or other authoritative references.

You should:

- Propose a `subtitle` based on the page's purpose and intended readers.
- Recommend `audience`, `topics`, and `components` using the definitions and selection guidance in `content-model.yml`.
- Refine the `description` during outlining or drafting when appropriate, subject to user approval.
- Automatically populate `last_modified` when creating the page.
- Ask for clarification if essential information is missing or the intended scope is unclear.

### Review project context

Before creating the outline:

1. Read the Documentation map in `AGENTS.md` to identify relevant source code, documentation, specifications, and other sources of truth.
2. Read `doc-infrastructure/content-model.yml` to understand the required metadata, allowed values, and selection guidance.
3. Review the template associated with the selected `content_type` in `doc-infrastructure/templates/`.
4. Review relevant existing documentation to establish context, maintain consistent terminology, and avoid duplicating content.

Use authoritative sources to determine what the page should cover. Distinguish implemented behavior from planned functionality. Do not invent technical details.

### Select initial metadata

Recommend `audience`, `topics`, and `components` based on the page's purpose, intended readers, summary, context sources, and proposed outline.

Use each value's `description` and `use_when` guidance in `content-model.yml`.

Apply these rules:

- **Audience:** Select `primary`, `secondary`, or both when the page meaningfully serves those audiences.
- **Topics:** Select the most specific relevant topics. Do not automatically include parent topics when selecting their children. Include a parent topic only if the page also substantially covers the broader subject.
- **Components:** Select components the page meaningfully describes, configures, operates, evaluates, or integrates with.
- **Relevance:** Do not select topics, components, or audiences based solely on passing references.
- **Controlled values:** Use only approved values from `content-model.yml`. Do not invent metadata values.

Treat the selections as provisional. Revisit them in Step 4 against the completed page.

### Create the outline

Draft a section-by-section outline that:

1. Follows the selected content-type template and its required structure.
2. Uses descriptive headings appropriate to the page's purpose.
3. Briefly identifies what each section will cover.
4. Identifies planned procedures, examples, code samples, or other supporting material when relevant.
5. Identifies unresolved questions, missing evidence, or technical details that require verification.

Keep the outline focused on the page's intended purpose. Do not write the full content during this step.

### Review and create the page

Present the following for user review:

- Proposed outline.
- Initial `audience`, `topics`, and `components` values.
- Questions or information gaps requiring resolution.

After approval, run `create_doc_page` to:

1. Create the MDX file in `fern/docs/pages/` using the selected content-type template.
2. Populate the initial frontmatter with approved values.
3. Set `lifecycle_status: draft`.
4. Set `last_modified` to the current date.
5. Update `doc-infrastructure/page-registry.yml`.
6. Add the approved outline to the new page.

Leave `prerequisites`, `next_steps`, and `related_pages` for Step 4.

**Stop after creating the page.** Wait for the user to request Step 2: Draft.

## Step 2: Create the draft

Using the approved outline from Step 1, write the first draft in the existing MDX file.

Focus on technical accuracy, completeness, and correct documentation structure. Follow the approved outline and the template associated with the page's `content_type`.

### Review project context

Before drafting:

1. Read `doc-infrastructure/technical-accuracy-rules.md` for technical accuracy, completeness, and verification requirements.
2. Read `doc-infrastructure/fern-platform-rules.md` for MDX formatting, internal links, and Fern components.
3. Read `doc-infrastructure/terminology.md` for preferred terminology and distinctions between project-specific concepts.
4. Review the authoritative context sources identified in Step 1. Consult additional sources when necessary to verify implementation details.
5. Review relevant existing documentation to maintain consistency and avoid duplicating information.

Use the Documentation map in `AGENTS.md` to locate additional sources of truth when needed.

### Write the draft

- Expand the approved outline into complete content.
- Follow the structure and requirements of the selected content-type template.
- Explain concepts, procedures, and system behavior at the level of detail needed by the intended audience.
- Base technical claims on authoritative sources. Distinguish implemented behavior from planned functionality.
- Apply the technical accuracy rules, including requirements for procedures, code examples, API details, and expected outcomes.
- Use preferred terminology consistently.
- Follow Fern platform rules for headings, links, code blocks, and reusable components.
- Include accurate code samples, commands, expected results, and examples where appropriate.
- Link to existing documentation when a subject is already covered in detail elsewhere.

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

Present the completed draft for user review.

Summarize:

- Unverified technical claims or examples.
- Missing information and unresolved questions.
- Significant changes from the approved outline that require approval.

Keep `lifecycle_status: draft`.

Do not perform the full editorial review during this step. Apply the writing style guide, including voice and tone and AI-generated content fingerprints, in Step 3.

**Stop and wait for user approval before proceeding to Step 3: Final draft.**

## Step 3: Create the final draft

Review and refine the approved draft from Step 2 to improve clarity, readability, consistency, and editorial quality.

Focus on producing documentation that follows the project's writing standards while preserving technical accuracy and the intended meaning.

### Review project standards

Before editing:

1. Read `doc-infrastructure/style-guide.md` for voice, tone, readability, structure, and editorial standards.
2. Read the **Avoid AI-generated content fingerprints** section of the style guide and apply its guidance throughout the review.
3. Review `doc-infrastructure/terminology.md` for preferred terminology and distinctions between project-specific concepts.
4. Refer to `doc-infrastructure/technical-accuracy-rules.md` when editing technical explanations or resolving accuracy concerns.

### Edit the draft

Review and edit the draft in the following sequence. Complete each pass before moving to the next, but revisit earlier decisions when necessary.

#### Pass 1: Review structure and flow

Review the page as a whole before editing individual sentences.

- Confirm that the content follows the approved outline and the appropriate content-type template.
- Check that sections follow a logical progression and support the page's purpose.
- Review headings for clarity, specificity, and proper hierarchy.
- Remove unnecessary sections and identify information that is missing or misplaced.
- Check that sections contain enough local context to remain understandable when retrieved independently, without unnecessary repetition.
- Review cross-references and remove duplicated explanations when an authoritative page already covers the subject.

Preserve the approved scope. Flag substantial structural changes for user review.

#### Pass 2: Edit for clarity and conciseness

Make the content easier to understand without removing necessary technical detail.

- Replace vague or abstract wording with concrete descriptions.
- Simplify unnecessarily complicated sentences.
- Remove filler, subjective claims, and redundant explanations.
- Eliminate unnecessary hedging while preserving meaningful conditions and uncertainty.
- Check that procedures, explanations, and examples provide enough information for the intended audience.
- Remove background information that does not help the reader accomplish the page's purpose.

#### Pass 3: Apply voice and tone

Apply the Voice and Tone rules in `doc-infrastructure/style-guide.md`.

- Use the project's warm, relaxed, knowledgeable voice.
- Prefer active voice and present tense.
- Address the reader directly when appropriate, especially in task-based documentation.
- Use common contractions naturally.
- Remove slang, unnecessary idioms, and Latin abbreviations.
- Vary sentence length and structure to maintain a natural reading flow.

Keep the tone appropriate to the page's content type and intended audience.

#### Pass 4: Review terminology

Apply the rules in `doc-infrastructure/terminology.md`.

- Replace nonpreferred terminology with approved terms.
- Preserve distinctions between related technical concepts.
- Check that project-specific terms are used consistently.
- Define acronyms on first use when required.
- Identify terminology gaps or conflicts that need a decision.

Do not introduce alternative terms merely to vary the language.

#### Pass 5: Remove AI-generated content fingerprints

Review the complete page against **Avoid AI-generated content fingerprints** in `doc-infrastructure/style-guide.md`.

Pay particular attention to:

- Formulaic introductions, transitions, and conclusions.
- Artificial contrasts and exaggerated claims.
- Generic examples and vague descriptions.
- Repetitive sentence patterns.
- Unnecessary formatting and excessive structure.
- Explanations that repeat information the intended audience already understands.

Revise passages that exhibit these patterns without making the writing less natural or technically precise.

Do not remove useful language solely because it resembles a listed pattern. Apply the style guide's **Use judgment** guidance.

#### Pass 6: Perform a final accuracy and consistency check

Read the revised page from beginning to end.

- Confirm that editorial changes have preserved technical meaning.
- Recheck technical claims that were substantially rewritten.
- Resolve outstanding accuracy questions from Step 2 where possible.
- Verify any new technical information introduced during editing.
- Confirm that conditions, limitations, warnings, examples, and expected outcomes remain accurate.
- Check for inconsistent wording or unintended repetition introduced during editing.

Do not repeat technical verification already completed in Step 2 unless a claim has changed or new uncertainty has been introduced.

Record unresolved issues for user review.

### Review technical accuracy

Confirm that editorial changes have not altered technical meaning.

- Recheck technical claims that were substantially rewritten.
- Resolve outstanding accuracy questions from Step 2.
- Verify any new examples, commands, or factual information introduced during editing.
- Preserve important conditions, limitations, warnings, and expected outcomes.

Do not repeat verification already completed in Step 2 unless the underlying information has changed or new uncertainty has been introduced.

If an accuracy issue remains unresolved, identify it for user review rather than presenting the claim as verified.

### Run editorial and documentation checks

Run the documentation validation command described in `doc-infrastructure/README.md`. Resolve issues introduced by your changes and report any remaining failures.

Review the results and correct issues within the scope of the page.

Do not automatically rewrite technically accurate content solely to satisfy a stylistic suggestion when doing so would reduce clarity or precision.

Report checks that could not be completed.

### Review the final draft

Present the revised page for user review.

Summarize:

- Significant editorial changes.
- Any remaining technical questions or unresolved issues.
- Validation results, including checks that could not be completed.

Keep `lifecycle_status: draft`.

**Stop and wait for user approval before proceeding to Step 4: Finalize metadata.**

## Step 4: Finalize metadata and page relationships

After the final draft is approved, finalize the page's metadata, relationships, and navigation.

### Review metadata

1. Review `doc-infrastructure/content-model.yml`, including the definitions and `use_when` guidance.
2. Review the `audience`, `topics`, and `components` selected in Step 1 against the completed page.
3. Add, remove, or change values as needed to accurately reflect the page's content.
4. Review the `description` and `subtitle` to ensure they represent the finished page.
5. Preserve the page's `id` and `content_type` unless a change is approved.

Use only allowed values from the content model. Assign topics and components based on the page's substantive coverage, not passing mentions.

### Finalize page relationships

Review the documentation IA, `page-registry.yml`, and existing documentation to identify:

- `prerequisites`: Pages readers should understand or complete before using this page.
- `next_steps`: Pages that provide a logical continuation or next action.
- `related_pages`: Pages covering complementary information.

Use registered page IDs for all relationships.

Add only relationships that serve a clear purpose. Avoid assigning the same page to multiple relationship fields unless justified.

For existing pages that should reference the new page:

1. Identify the affected pages and explain the proposed changes.
2. Present the changes for user approval.
3. Update existing pages only after approval.

### Update and validate

1. Update the new page's frontmatter with the finalized metadata and relationships.
2. Apply approved changes to existing pages.
3. Add the new page to the appropriate location in `fern/docs.yml`, if it isn't already included.
4. Update `last_modified` using the command documented in `doc-infrastructure/README.md`.
5. Run the regular documentation validation command documented in `doc-infrastructure/README.md`.
6. Resolve issues introduced by your changes and report any remaining failures.

Keep `lifecycle_status: review` until the completed page and metadata receive user approval.

### Final approval

Present a summary of:

- Final metadata values.
- Added or updated page relationships.
- Navigation changes.
- Validation results.
- Any unresolved questions.

After user approval:

1. Set `lifecycle_status: published`.
2. Run the production documentation validation command documented in `doc-infrastructure/README.md`.
3. Resolve any failures and report the final validation results.

Do not commit or push changes unless explicitly requested. GitHub Actions handles publishing when changes are pushed to the publishing branch.