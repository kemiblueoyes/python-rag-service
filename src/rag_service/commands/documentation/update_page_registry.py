"""Generate the documentation page registry from canonical sources."""

from __future__ import annotations

import argparse
from pathlib import Path

from rag_service.commands.documentation.validate_frontmatter import (
    FrontmatterValidationError,
    load_content_model,
    parse_frontmatter,
)

REPO_ROOT = Path(__file__).resolve().parents[4]

PAGES_DIR = (
    REPO_ROOT
    / "fern"
    / "docs"
    / "pages"
)

REGISTRY_PATH = (
    REPO_ROOT
    / "doc-infrastructure"
    / "page-registry.yml"
)

GENERATED_PAGES = [
    {
        "id": "SrchAPI",
        "content_type": "api_reference",
    },
    {
        "id": "AnsAPI",
        "content_type": "api_reference",
    },
    {
        "id": "HlthAPI",
        "content_type": "api_reference",
    },
]

GENERATED_HEADER = """\
# GENERATED FILE — DO NOT EDIT DIRECTLY.
#
# Sources:
# - fern/docs/pages/**/*.mdx
# - generated API reference page IDs defined in update_page_registry.py
#
# Regenerate with:
#   uv run python -m rag_service.commands.documentation.update_page_registry

"""


class PageRegistrySyncError(ValueError):
    """Raised when page-registry sources are invalid."""


def collect_mdx_pages(
    pages_dir: Path = PAGES_DIR,
) -> list[dict[str, str]]:
    """Collect active canonical pages from MDX frontmatter."""
    model = load_content_model()
    pages: list[dict[str, str]] = []
    seen_ids: dict[str, Path] = {}

    for path in sorted(pages_dir.rglob("*.mdx")):
        try:
            frontmatter = parse_frontmatter(path)
        except FrontmatterValidationError as exc:
            raise PageRegistrySyncError(
                "\n".join(exc.errors)
            ) from exc

        page_id = frontmatter.get("id")
        content_type = frontmatter.get("content_type")
        lifecycle_status = frontmatter.get(
            "lifecycle_status"
        )

        if (
            not isinstance(page_id, str)
            or not page_id.strip()
        ):
            raise PageRegistrySyncError(
                f"{path}: missing or invalid 'id'."
            )

        if (
            not isinstance(content_type, str)
            or content_type not in model.content_types
        ):
            raise PageRegistrySyncError(
                f"{path}: missing or invalid "
                "'content_type'."
            )

        if (
            not isinstance(lifecycle_status, str)
            or lifecycle_status
            not in model.lifecycle_statuses
        ):
            raise PageRegistrySyncError(
                f"{path}: missing or invalid "
                "'lifecycle_status'."
            )

        # Archived pages are no longer active relationship targets.
        if lifecycle_status == "archived":
            continue

        page_id = page_id.strip()

        if page_id in seen_ids:
            raise PageRegistrySyncError(
                f"{path}: duplicate page id {page_id!r}; "
                f"already used by {seen_ids[page_id]}."
            )

        seen_ids[page_id] = path

        pages.append(
            {
                "id": page_id,
                "content_type": content_type,
            }
        )

    return pages


def combine_pages(
    mdx_pages: list[dict[str, str]],
    generated_pages: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Combine page sources and reject duplicate IDs."""
    pages: dict[str, dict[str, str]] = {}

    for page in [
        *mdx_pages,
        *generated_pages,
    ]:
        page_id = page["id"]

        if page_id in pages:
            raise PageRegistrySyncError(
                f"Duplicate canonical page id "
                f"{page_id!r} across registry sources."
            )

        pages[page_id] = page

    return sorted(
        pages.values(),
        key=lambda page: page["id"],
    )


def render_registry(
    pages: list[dict[str, str]],
) -> str:
    """Render page-registry.yml deterministically."""
    lines = [
        GENERATED_HEADER.rstrip(),
        "",
        "version: 1",
        "",
        "pages:",
    ]

    for page in pages:
        lines.extend(
            [
                f"  - id: {page['id']}",
                (
                    "    content_type: "
                    f"{page['content_type']}"
                ),
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def expected_registry() -> str:
    """Return the registry derived from canonical sources."""
    return render_registry(
        combine_pages(
            collect_mdx_pages(),
            GENERATED_PAGES,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate or validate the documentation "
            "page registry."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Check whether page-registry.yml is current "
            "without modifying it."
        ),
    )

    args = parser.parse_args()

    try:
        expected = expected_registry()
    except PageRegistrySyncError as exc:
        print(f"Page registry generation failed:\n\n{exc}")
        return 1

    if args.check:
        if (
            not REGISTRY_PATH.is_file()
            or REGISTRY_PATH.read_text(
                encoding="utf-8"
            )
            != expected
        ):
            print(
                "Page registry is out of date.\n\n"
                "Run:\n"
                "uv run python -m "
                "rag_service.commands.documentation."
                "update_page_registry"
            )
            return 1

        print("Page registry is current.")
        return 0

    previous = (
        REGISTRY_PATH.read_text(encoding="utf-8")
        if REGISTRY_PATH.is_file()
        else None
    )

    if previous == expected:
        print("Page registry is already current.")
        return 0

    REGISTRY_PATH.write_text(
        expected,
        encoding="utf-8",
    )

    print(
        "Updated "
        "doc-infrastructure/page-registry.yml."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())