---
name: update-glossary
description: >-
  Add or revise Python RAG Service glossary entries in docs/data/glossary.yml,
  check project terminology and implementation evidence, flag terminology
  decisions for human review, and regenerate the glossary and Vale vocabulary.
  Use for named-term updates or reviewing a feature area to recommend glossary
  additions and revisions, not general documentation audits or spelling
  allowlist changes alone.
---

# Update the glossary

Use the requested terms and scope. If no term or topic can be inferred, ask what
to define before editing. A request to recommend, draft, or review entries alone
does not authorize updating the source or running the generator in write mode.

Maintain reader-facing definitions in docs/data/glossary.yml. Run commands from the repository root.
Follow the checkout and preservation instructions in AGENTS.md.

## Choose the discovery scope

- **Term-driven:** For a request such as "Add reciprocal rank fusion to the
  glossary," use the named concept as the scope for Steps 1–3.
- **Feature-driven:** For a request such as "Review the new automation and
  operations capabilities and recommend glossary additions or updates," use
  the specified feature area as the scope for Steps 1–3. Discover candidate
  concepts from its documentation and implementation before drafting entries.

For feature-driven requests, identify the relevant capabilities and sources
using the documentation map in `AGENTS.md`. Use a supplied PR, change range,
release, or file list to narrow the review. If "new" has no clear baseline,
state the feature area and current checkout being reviewed; ask for a baseline
only when it materially changes the review. Do not imply a complete change
audit without evidence of that scope.

Review terminology rules and existing glossary coverage before investigating the feature.
Revisit both resources as candidate terms are discovered and evaluated.
Compare each candidate with the rules and entries already reviewed. Favor
concepts readers need to understand the capabilities, rather than listing every
class, setting, command, or implementation detail.

At the end of Step 3, recommend additions or revisions with a brief reason and
supporting file references to the relevant help documentation. Include implementation references only when the documentation is missing, insufficient, or inconsistent with the implementation, or when a technical claim requires additional evidence. Identify existing entry IDs for revisions and note
relevant concepts already adequately covered. Do not force additions when the
existing glossary is sufficient. State any limits on the sources reviewed.

Continue to Step 4 to draft the recommended changes and Step 5 to present them
for approval. Keep recommendations and drafts read-only until the user approves
applying specific entries. If the user asks only for a candidate list or
explicitly excludes drafting, stop after the recommendations.

## 1. Review terminology

Read `doc-infrastructure/terminology.md` first. Identify preferred names,
discouraged variants, and distinctions that apply to each requested concept.
Terminology rules govern word choice; the glossary explains meaning; Vale
enforces selected rules.

Read `doc-infrastructure/README.md`, `doc-infrastructure/style-guide.md`, and
`doc-infrastructure/technical-accuracy-rules.md` for the maintained authoring
and validation guidance.

## 2. Review existing entries

Inspect `docs/data/glossary.yml`, including canonical names, aliases,
definitions, and related terms. Search for spelling variants, acronyms, and
equivalent concepts, not just the requested spelling.

- If an existing entry already describes the requested concept, determine whether a
revision is necessary. Do not create a duplicate entry or revise an adequate definition
unnecessarily. Preserve the existing ID when revising an entry.
- Check aliases against other entries' names and aliases. The generator checks
  duplicate aliases within an entry, but does not resolve cross-entry collisions
  or semantic duplicates.
- Keep distinct concepts separate even when their wording is similar. Do not
  turn a discouraged variant or a term with a different project meaning into an
  accepted alias.
- Add definitions when they help readers understand the documentation. A
  spelling allowance alone belongs in
  `styles/config/vocabularies/RAGService/manual-accept.txt`; explain that route
  rather than inventing a definition.

## 3. Establish the project meaning

Use the documentation map in `AGENTS.md` to locate relevant sources. For
project-specific terms or definitions that describe system behavior, verify the
meaning against the relevant implementation, configuration, and tests. For
general industry terms, review how the term is used in the documentation and
verify any claims about project-specific behavior.

Limit investigation to the sources necessary to establish an accurate definition.

Keep file and line references for the claims in the proposed definition.
Distinguish current behavior from plans, general industry concepts, and recorded
evaluation results. If documentation and implementation disagree, surface the
discrepancy instead of publishing an unverified claim.

## 4. Draft the entry

Follow the existing entry structure in `docs/data/glossary.yml`.
Draft only the YAML entry; the generator handles the published glossary
and Vale vocabulary.

For schema version 1:

- Keep the top-level `version: 1` and `terms` list.
- Use `id`, `term`, and `definition` for every entry. IDs are unique lowercase
  kebab-case beginning with a letter. Canonical names are unique without regard
  to case and begin with a letter.
- Write a concise, standalone definition of the concept. Include project-specific
  context when it helps the reader understand how the Python RAG Service uses or  
  implements the concept. Use folded YAML strings (`>`) as in existing entries.
- Add `example` only when a short, concrete example clarifies the definition.
- Add `aliases` only for useful, accepted synonyms or acronyms. These are
  published as “Also known as” and enter the generated Vale vocabulary.
- Use existing entry IDs or IDs of entries proposed in the same update in `related_terms`,
  without self-references. Before applying approved entries, verify that all referenced IDs
  will exist in the updated glossary. Do not add unapproved entries to satisfy relationships. Add only
  useful relationships, not every nearby concept.

Adhere to editorial requirements: 
- Define one concept per entry.
- Avoid circular definitions.
- Avoid using the glossary as a substitute for detailed architecture or procedural documentation.
- Include examples that clarify meaning rather than repeat the definition.
- Ensure each definition makes sense when read independently.

Omit unused optional fields. Preserve source organization; the generator sorts
the published glossary alphabetically. Keep internal verification notes out of
the published definition.

## 5. Surface terminology decisions and request approval

If the draft conflicts with an existing terminology rule, introduces a preferred
name that needs a decision, or leaves a material meaning unresolved, present the
proposed entry, the conflicting rule or evidence with file references, and a
concrete recommendation for human review. Explain which decision prevents the
affected entry from being finalized. Continue independent entries that do not
depend on that decision.

Use decisions the user has already made. Routine additions need no separate
terminology decision, but still require approval of the draft entry. Do not
silently change `terminology.md` or Vale rules as part of a glossary update.
When a terminology decision is required, recommend the necessary changes to
`terminology.md` or Vale rules. Do not modify these files unless the user explicitly
requests it. Resolve the terminology decision before applying the affected glossary entry.

Present all proposed glossary entries together for human review, including their
definitions, optional fields, and any terminology decisions or unresolved questions.

Allow the user to approve, reject, or request revisions to individual entries. Do not
assume approval of the entire list when only some entries are approved.

Wait for explicit approval before updating `docs/data/glossary.yml`. Apply only
approved entries.

## 6. Update the source

Apply the approved entry changes to `docs/data/glossary.yml`. Preserve other
edits and avoid unrelated glossary cleanup. Never edit generated glossary prose,
date metadata, or `accept.txt` by hand.

## 7. Generate and verify

Run the existing generator; do not duplicate its validation or rendering in a
new script:

```bash
uv run python scripts/generate_glossary.py
uv run python scripts/generate_glossary.py --check
```

The generator validates structure and produces:

- `fern/docs/pages/reference/glossary.mdx`, including its date metadata.
- `styles/config/vocabularies/RAGService/accept.txt`, merging canonical names
  and aliases with `manual-accept.txt`.

Correct source errors and rerun if generation fails. A successful generator run
does not establish semantic accuracy or override separate Vale terminology
rules.

Review the source and generated diffs for the intended definitions, aliases,
related links, and vocabulary changes. Follow `doc-infrastructure/README.md` for
validation; for glossary updates, run:

```bash
npm run lint:docs
uv run python -m rag_service.commands.documentation.validate_docs
```

Report failures or missing prerequisites accurately. Do not repair unrelated
documentation failures as part of this task.

Finish with the terms added or revised, supporting source references, unresolved
decisions, generated files changed, and validation results. Include the checkout
path and branch or detached HEAD state, verify changes with Git status and diff,
and leave edits unstaged and uncommitted unless requested otherwise.
