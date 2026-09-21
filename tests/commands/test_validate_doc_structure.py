from pathlib import Path

from rag_service.commands.documentation.validate_doc_structure import (
    validate_document_structure,
    validate_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

TEST_TEMPLATE_DIR = (
    REPO_ROOT
    / "doc-infrastructure"
    / "templates"
    / "test-templates"
)

PAGE_FIXTURES = [
    TEST_TEMPLATE_DIR / "overview_Home.mdx",
    TEST_TEMPLATE_DIR / "how-to_Search-documentation.mdx",
    TEST_TEMPLATE_DIR / "tutorial_Build-inspect-your-first-doc-index.mdx",
    TEST_TEMPLATE_DIR / "explanation_Retrieval-pipeline.mdx",
    TEST_TEMPLATE_DIR / "general-reference_Configuration-reference.mdx",
    TEST_TEMPLATE_DIR / "general-reference_Glossary.mdx",
    TEST_TEMPLATE_DIR / "evaluation-results_Current-evaluation-results.mdx",
    TEST_TEMPLATE_DIR / "release-note_Hybrid-retrieval.mdx",
]


def test_realistic_page_templates_pass_structure_validation() -> None:
    errors = validate_paths(PAGE_FIXTURES)

    assert errors == []


def test_h1_is_rejected(tmp_path: Path) -> None:
    page = tmp_path / "h1.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test
description: Test
content_type: general_reference
lifecycle_status: draft
topics: [topic-architecture]
last_modified: 2026-09-20
---

# Test

## Reference information
""",
        encoding="utf-8",
    )

    errors = validate_document_structure(page)

    assert any(
        "must not contain an H1" in error
        for error in errors
    )


def test_overview_requires_key_capabilities(
    tmp_path: Path,
) -> None:
    page = tmp_path / "overview.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test
description: Test
content_type: overview
lifecycle_status: draft
topics: [topic-architecture]
last_modified: 2026-09-20
---

Introduction.

## Next steps

Continue.
""",
        encoding="utf-8",
    )

    errors = validate_document_structure(page)

    assert any(
        "missing required H2 heading 'Key capabilities'"
        in error
        for error in errors
    )


def test_how_to_requires_steps_component(
    tmp_path: Path,
) -> None:
    page = tmp_path / "how-to.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test
description: Test
content_type: how_to
lifecycle_status: draft
topics: [topic-api]
last_modified: 2026-09-20
---

Complete the task.

## Next steps

Continue.
""",
        encoding="utf-8",
    )

    errors = validate_document_structure(page)

    assert any(
        "must contain exactly one <Steps> component"
        in error
        for error in errors
    )


def test_how_to_rejects_goal_heading(
    tmp_path: Path,
) -> None:
    page = tmp_path / "goal.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test
description: Test
content_type: how_to
lifecycle_status: draft
topics: [topic-api]
last_modified: 2026-09-20
---

## Goal

Complete the task.

<Steps toc={true}>

## Do the thing

Do it.

</Steps>
""",
        encoding="utf-8",
    )

    errors = validate_document_structure(page)

    assert any(
        "must not use an H2 'Goal' heading"
        in error
        for error in errors
    )


def test_tutorial_requires_what_you_learned(
    tmp_path: Path,
) -> None:
    page = tmp_path / "tutorial.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test
description: Test
content_type: tutorial
lifecycle_status: draft
topics: [topic-indexing]
last_modified: 2026-09-20
---

Introduction.

## Prerequisites

Requirements.

<Steps toc={true}>

## Build something

Build it.

</Steps>

## Next steps

Continue.
""",
        encoding="utf-8",
    )

    errors = validate_document_structure(page)

    assert any(
        "missing required H2 heading 'What you learned'"
        in error
        for error in errors
    )


def test_eval_results_requires_results_section(
    tmp_path: Path,
) -> None:
    page = tmp_path / "evaluation.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test
description: Test
content_type: eval_results
lifecycle_status: draft
topics: [topic-evaluation]
dataset_version: test
last_modified: 2026-09-20
---

Introduction.

## Evaluation dataset

Dataset.

## Findings

Findings.

## Limitations

Limitations.
""",
        encoding="utf-8",
    )

    errors = validate_document_structure(page)

    assert any(
        "must contain at least one H2 results section"
        in error
        for error in errors
    )