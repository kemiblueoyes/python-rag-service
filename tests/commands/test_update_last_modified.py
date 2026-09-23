import subprocess
from datetime import date
from pathlib import Path

import pytest

from rag_service.commands.documentation.update_last_modified import (
    LastModifiedError,
    git_last_modified_date,
    render_last_modified,
)


def test_replaces_existing_last_modified() -> None:
    source = """\
---
title: Test page
last_modified: 2026-01-01
---

Content.
"""

    result = render_last_modified(
        source,
        "2026-09-23",
    )

    assert "last_modified: 2026-09-23" in result
    assert "last_modified: 2026-01-01" not in result


def test_adds_missing_last_modified() -> None:
    source = """\
---
title: Test page
---

Content.
"""

    result = render_last_modified(
        source,
        "2026-09-23",
    )

    assert (
        "title: Test page\n"
        "last_modified: 2026-09-23\n"
        "---"
        in result
    )


def test_does_not_replace_body_text() -> None:
    source = """\
---
title: Test page
---

Example:

last_modified: not-frontmatter
"""

    result = render_last_modified(
        source,
        "2026-09-23",
    )

    assert "last_modified: 2026-09-23" in result
    assert "last_modified: not-frontmatter" in result


def test_rejects_missing_frontmatter() -> None:
    with pytest.raises(
        LastModifiedError,
        match="missing YAML frontmatter",
    ):
        render_last_modified(
            "Content only.",
            "2026-09-23",
        )

def initialize_git_repo(tmp_path: Path) -> Path:
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
    )

    return tmp_path


def test_last_modified_ignores_metadata_only_change(
    tmp_path: Path,
) -> None:
    repo = initialize_git_repo(tmp_path)
    page = repo / "page.mdx"

    page.write_text(
        """\
---
title: Test
last_modified: 2026-01-01
---

Content.
""",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "add", "page.mdx"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add page"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    committed_date = git_last_modified_date(
        page,
        repo_root=repo,
    )

    page.write_text(
        """\
---
title: Test
last_modified: 2026-09-23
---

Content.
""",
        encoding="utf-8",
    )

    assert (
        git_last_modified_date(
            page,
            repo_root=repo,
        )
        == committed_date
    )


def test_last_modified_uses_today_for_content_change(
    tmp_path: Path,
) -> None:
    repo = initialize_git_repo(tmp_path)
    page = repo / "page.mdx"

    page.write_text(
        """\
---
title: Test
last_modified: 2026-01-01
---

Original content.
""",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "add", "page.mdx"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add page"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    page.write_text(
        """\
---
title: Test
last_modified: 2026-01-01
---

Updated content.
""",
        encoding="utf-8",
    )

    assert git_last_modified_date(
        page,
        repo_root=repo,
    ) == date.today().isoformat()