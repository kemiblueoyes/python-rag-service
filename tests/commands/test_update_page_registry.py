from pathlib import Path

import pytest

from rag_service.commands.documentation.update_page_registry import (
    PageRegistrySyncError,
    collect_mdx_pages,
    combine_pages,
    render_registry,
)


def test_collects_id_and_content_type_from_mdx(
    tmp_path: Path,
) -> None:
    page = tmp_path / "example.mdx"

    page.write_text(
        """\
---
id: Example
title: Example
subtitle: Example subtitle
description: Example description
content_type: how_to
lifecycle_status: draft
topics: [topic-api]
audience: [primary]
last_modified: 2026-10-07
---

Content.
""",
        encoding="utf-8",
    )

    pages = collect_mdx_pages(tmp_path)

    assert pages == [
        {
            "id": "Example",
            "content_type": "how_to",
        }
    ]


def test_archived_pages_are_excluded(
    tmp_path: Path,
) -> None:
    page = tmp_path / "archived.mdx"

    page.write_text(
        """\
---
id: Archived
title: Archived
subtitle: Archived subtitle
description: Archived description
content_type: explanation
lifecycle_status: archived
topics: [topic-architecture]
audience: [secondary]
last_modified: 2026-10-07
---

Content.
""",
        encoding="utf-8",
    )

    assert collect_mdx_pages(tmp_path) == []


def test_combine_pages_rejects_duplicate_ids() -> None:
    with pytest.raises(
        PageRegistrySyncError,
        match="Duplicate canonical page id",
    ):
        combine_pages(
            [
                {
                    "id": "SrchAPI",
                    "content_type": "overview",
                }
            ],
            [
                {
                    "id": "SrchAPI",
                    "content_type": "api_reference",
                }
            ],
        )


def test_render_registry_is_deterministic() -> None:
    result = render_registry(
        [
            {
                "id": "BPage",
                "content_type": "how_to",
            },
            {
                "id": "APage",
                "content_type": "overview",
            },
        ]
    )

    assert "version: 1" in result
    assert result.index("id: BPage") < result.index("id: APage")