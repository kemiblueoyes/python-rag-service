# Doc infrastructure changelog

## Flowchart colors publish from CI (2026-11-27)

- On `main`, CI runs `python doc-infrastructure/scripts/fern_mermaid.py prepare` before it publishes documentation.
The command stages `.generated/fern/` with shared flowchart colors, and CI publishes that copy.

## Changelog and glossary skills added (2026-11-27)

- The `add-changelog-entry` skill adds a release note in `fern/docs/pages/changelog/` from pull requests, commits, diffs, or supplied context. It follows the release-note template and the documentation style guide.
- The `update-glossary` skill adds or revises glossary entries in `docs/data/glossary.yml`. It checks project terminology and implementation evidence, flags terminology decisions for human review, and regenerates the glossary and Vale vocabulary.

## Shared flowchart colors for documentation preview (2026-11-25)

- Documentation authors can preview flowchart diagrams with one shared color palette.
- `doc-infrastructure/scripts/fern_mermaid.py` reads those colors from `doc-infrastructure/diagram-styles/mermaid-theme.json` and writes them into a copy of the Fern site.
- The script copies `fern/` to `.generated/fern/` and adds shared `classDef` colors to `flowchart` and `graph` blocks.
- Authored pages under `fern/` stay unchanged.

## Documentation accuracy checks added (2026-11-11)

- `AGENTS.md` is repository guidance for documentation work. It points to each docs area and the code to compare it with. Use it before you write, review, or audit a page.
- The `docs-sync-audit` skill checks whether the docs still match the repository. Use it to find stale or missing docs without changing files.
- Factual-writing guidance moved out of the style guide into `technical-accuracy-rules.md`. Use it when you draft or review a page so the claims match the implementation.
