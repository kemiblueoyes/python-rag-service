"""Production lifecycle checks must block unpublished Fern content."""

from pathlib import Path

import pytest

from rag_service.commands.documentation.validate_docs import validate_production_pages


@pytest.mark.parametrize("status", ["published", "deprecated"])
def test_publishable_statuses_pass(tmp_path: Path, status: str) -> None:
    page = tmp_path / "page.mdx"
    page.write_text(f"---\nlifecycle_status: {status}\n---\n", encoding="utf-8")
    assert validate_production_pages([page]) == []


@pytest.mark.parametrize(
    "status", ["draft", "review", "archived", "unknown", "[published]"]
)
def test_unpublishable_statuses_fail(tmp_path: Path, status: str) -> None:
    # This includes pages omitted from navigation: all production source is checked.
    page = tmp_path / "unlisted.mdx"
    page.write_text(f"---\nlifecycle_status: {status}\n---\n", encoding="utf-8")
    errors = validate_production_pages([page])
    assert len(errors) == 1
    assert "production pages must use lifecycle_status" in errors[0]


def test_missing_status_fails(tmp_path: Path) -> None:
    page = tmp_path / "page.mdx"
    page.write_text("---\ntitle: Page\n---\n", encoding="utf-8")
    assert validate_production_pages([page])


@pytest.mark.parametrize("draft", ["true", "'false'", "0", "null"])
def test_fern_draft_cannot_override_published_status(
    tmp_path: Path, draft: str
) -> None:
    page = tmp_path / "release.mdx"
    page.write_text(
        f"---\nlifecycle_status: published\ndraft: {draft}\n---\n",
        encoding="utf-8",
    )
    assert "cannot set Fern 'draft'" in validate_production_pages([page])[0]


def test_explicit_false_draft_passes(tmp_path: Path) -> None:
    page = tmp_path / "release.mdx"
    page.write_text(
        "---\nlifecycle_status: published\ndraft: false\n---\n", encoding="utf-8"
    )
    assert validate_production_pages([page]) == []


def test_malformed_frontmatter_fails(tmp_path: Path) -> None:
    page = tmp_path / "page.mdx"
    page.write_text("No frontmatter", encoding="utf-8")
    assert "missing YAML frontmatter" in validate_production_pages([page])[0]
