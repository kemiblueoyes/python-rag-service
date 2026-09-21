from pathlib import Path

from rag_service.commands.documentation.validate_frontmatter import (
    ContentModel,
    PageRegistry,
    load_content_model,
    load_page_registry,
    validate_document,
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


def test_realistic_page_templates_pass_frontmatter_validation() -> None:
    model, registry = load_validation_contracts()

    errors = validate_paths(
        PAGE_FIXTURES,
        model,
        registry,
    )

    assert errors == []


def test_missing_required_field_is_rejected(tmp_path: Path) -> None:
    page = tmp_path / "missing-title.mdx"
    page.write_text(
        """\
---
id: Test
subtitle: Test subtitle
description: Test description
content_type: overview
lifecycle_status: draft
topics: [topic-architecture]
last_modified: 2026-09-20
---

Test content.
""",
        encoding="utf-8",
    )

    model, registry = load_validation_contracts()

    errors = validate_document(page, model, registry)

    assert any(
        "missing required field 'title'" in error
        for error in errors
    )


def test_unknown_content_type_is_rejected(tmp_path: Path) -> None:
    page = tmp_path / "bad-content-type.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test subtitle
description: Test description
content_type: guide
lifecycle_status: draft
topics: [topic-architecture]
last_modified: 2026-09-20
---

Test content.
""",
        encoding="utf-8",
    )

    model, registry = load_validation_contracts()

    errors = validate_document(page, model, registry)

    assert any(
        "unknown content_type 'guide'" in error
        for error in errors
    )


def test_unknown_controlled_topic_is_rejected(tmp_path: Path) -> None:
    page = tmp_path / "bad-topic.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test subtitle
description: Test description
content_type: overview
lifecycle_status: draft
topics: [retrieval]
last_modified: 2026-09-20
---

Test content.
""",
        encoding="utf-8",
    )

    model, registry = load_validation_contracts()

    errors = validate_document(page, model, registry)

    assert any(
        "unknown topic 'retrieval'" in error
        for error in errors
    )


def test_relationship_metadata_must_be_a_list(
    tmp_path: Path,
) -> None:
    page = tmp_path / "bad-relationship.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test subtitle
description: Test description
content_type: overview
lifecycle_status: draft
topics: [topic-architecture]
next_steps: Qstrt
last_modified: 2026-09-20
---

Test content.
""",
        encoding="utf-8",
    )

    model, registry = load_validation_contracts()

    errors = validate_document(page, model, registry)

    assert any(
        "'next_steps' must be a list" in error
        for error in errors
    )


def test_eval_results_requires_dataset_version(
    tmp_path: Path,
) -> None:
    page = tmp_path / "bad-eval.mdx"
    page.write_text(
        """\
---
id: Eval
title: Evaluation results
subtitle: Review evaluation results.
description: Current evaluation results.
content_type: eval_results
lifecycle_status: draft
topics: [topic-evaluation]
last_modified: 2026-09-20
---

Test content.
""",
        encoding="utf-8",
    )

    model, registry = load_validation_contracts()

    errors = validate_document(page, model, registry)

    assert any(
        "missing required field 'dataset_version'" in error
        for error in errors
    )


def test_duplicate_page_ids_are_rejected(tmp_path: Path) -> None:
    frontmatter = """\
---
id: Duplicate
title: Test
subtitle: Test subtitle
description: Test description
content_type: overview
lifecycle_status: draft
topics: [topic-architecture]
last_modified: 2026-09-20
---

Test content.
"""

    first = tmp_path / "first.mdx"
    second = tmp_path / "second.mdx"

    first.write_text(frontmatter, encoding="utf-8")
    second.write_text(frontmatter, encoding="utf-8")

    model, registry = load_validation_contracts()

    errors = validate_paths(
        [first, second],
        model,
        registry,
    )

    assert any(
        "duplicate id 'Duplicate'" in error
        for error in errors
    )

def load_validation_contracts() -> tuple[
    ContentModel,
    PageRegistry,
]:
    model = load_content_model()
    registry = load_page_registry(model)

    return model, registry

def test_unknown_relationship_target_is_rejected(
    tmp_path: Path,
) -> None:
    page = tmp_path / "bad-relationship.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test subtitle
description: Test description
content_type: overview
lifecycle_status: draft
topics: [topic-architecture]
next_steps: [NotARealPage]
last_modified: 2026-09-20
---

Test content.
""",
        encoding="utf-8",
    )

    model, registry = load_validation_contracts()

    errors = validate_document(
        page,
        model,
        registry,
    )

    assert any(
        "unknown page id 'NotARealPage'" in error
        for error in errors
    )


def test_page_cannot_reference_itself(
    tmp_path: Path,
) -> None:
    page = tmp_path / "self-reference.mdx"
    page.write_text(
        """\
---
id: Qstrt
title: Quickstart
subtitle: Get started.
description: Get started with the service.
content_type: how_to
lifecycle_status: draft
topics: [topic-installation]
related_pages: [Qstrt]
last_modified: 2026-09-20
---

Test content.
""",
        encoding="utf-8",
    )

    model, registry = load_validation_contracts()

    errors = validate_document(
        page,
        model,
        registry,
    )

    assert any(
        "cannot reference the page itself" in error
        for error in errors
    )


def test_duplicate_relationship_target_is_rejected(
    tmp_path: Path,
) -> None:
    page = tmp_path / "duplicate-relationship.mdx"
    page.write_text(
        """\
---
id: Test
title: Test
subtitle: Test subtitle
description: Test description
content_type: overview
lifecycle_status: draft
topics: [topic-architecture]
related_pages: [Qstrt, Qstrt]
last_modified: 2026-09-20
---

Test content.
""",
        encoding="utf-8",
    )

    model, registry = load_validation_contracts()

    errors = validate_document(
        page,
        model,
        registry,
    )

    assert any(
        "duplicate page id 'Qstrt'" in error
        for error in errors
    )


def test_registered_page_must_use_registered_content_type(
    tmp_path: Path,
) -> None:
    page = tmp_path / "wrong-content-type.mdx"
    page.write_text(
        """\
---
id: SrchDoc
title: Search documentation
subtitle: Search documentation.
description: Search indexed documentation.
content_type: overview
lifecycle_status: draft
topics: [topic-retrieval]
last_modified: 2026-09-20
---

Test content.
""",
        encoding="utf-8",
    )

    model, registry = load_validation_contracts()

    errors = validate_document(
        page,
        model,
        registry,
    )

    assert any(
        "page 'SrchDoc' must use content_type 'how_to'"
        in error
        for error in errors
    )