"""Create a new authored Fern documentation page.

components, prerequisites, next_steps, and related_pages are omitted when the IA has no values for them.

Example:

    uv run python -m \
      rag_service.commands.documentation.create_doc_page \
      --id NewGuide \
      --title "Configure a new provider" \
      --description "Configure a provider for the Python RAG service." \
      --content-type how_to \
      --topics topic-configuration topic-provider-configuration \
      --components component-public-api \
      --prerequisites ConfSrv \
      --next-steps IndxWP \
      --related-pages CnfgRef Auth \
      --audience primary \
      --path fern/docs/pages/get-started/configure-new-provider.mdx
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

from rag_service.commands.documentation.update_page_registry import (
    GENERATED_PAGES,
    collect_mdx_pages,
    update_registry,
)
from rag_service.commands.documentation.validate_frontmatter import (
    load_content_model,
)

REPO_ROOT = Path(__file__).resolve().parents[4]

PAGES_DIR = (
    REPO_ROOT
    / "fern"
    / "docs"
    / "pages"
)

FILENAME_PATTERN = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*\.mdx$"
)


class CreateDocPageError(ValueError):
    """Raised when a documentation page cannot be created."""


def resolve_page_path(value: Path) -> Path:
    """Resolve and validate a Fern documentation page path."""
    path = (
        value
        if value.is_absolute()
        else REPO_ROOT / value
    ).resolve()

    try:
        path.relative_to(PAGES_DIR.resolve())
    except ValueError as exc:
        raise CreateDocPageError(
            "Page path must be inside fern/docs/pages."
        ) from exc

    if not FILENAME_PATTERN.fullmatch(path.name):
        raise CreateDocPageError(
            "Page filename must use lowercase kebab-case "
            "and end in .mdx."
        )

    return path


def validate_page_id(page_id: str) -> str:
    """Validate that a page ID is non-empty and unique."""
    value = page_id.strip()

    if not value:
        raise CreateDocPageError(
            "Page ID must not be empty."
        )

    existing_pages = [
        *collect_mdx_pages(),
        *GENERATED_PAGES,
    ]

    if any(
        page["id"] == value
        for page in existing_pages
    ):
        raise CreateDocPageError(
            f"Page ID {value!r} already exists."
        )

    return value


def validate_content_type(
    content_type: str,
) -> str:
    """Validate an authored-page content type."""
    model = load_content_model()

    if content_type not in model.content_types:
        raise CreateDocPageError(
            f"Unknown content type {content_type!r}."
        )

    if content_type == "api_reference":
        raise CreateDocPageError(
            "API reference pages are generated from OpenAPI "
            "and should not be created as authored MDX pages."
        )

    return content_type


def validate_text(
    value: str,
    field: str,
) -> str:
    """Validate a required single-line text value."""
    stripped = value.strip()

    if not stripped:
        raise CreateDocPageError(
            f"{field!r} must not be empty."
        )

    if "\n" in stripped:
        raise CreateDocPageError(
            f"{field!r} must be a single line."
        )

    return stripped


def validate_values(
    values: list[str] | None,
    field: str,
    *,
    allowed: frozenset[str] | None = None,
    required: bool = False,
) -> list[str]:
    """Validate a list of metadata values."""
    if not values:
        if required:
            raise CreateDocPageError(
                f"{field!r} must contain at least one value."
            )

        return []

    cleaned: list[str] = []
    seen: set[str] = set()

    for value in values:
        item = value.strip()

        if not item:
            raise CreateDocPageError(
                f"{field!r} values must not be empty."
            )

        if item in seen:
            raise CreateDocPageError(
                f"{field!r} contains duplicate value "
                f"{item!r}."
            )

        if allowed is not None and item not in allowed:
            raise CreateDocPageError(
                f"Unknown {field} value {item!r}."
            )

        seen.add(item)
        cleaned.append(item)

    return cleaned


def render_scalar(
    field: str,
    value: str,
) -> str:
    """Render one YAML scalar field safely."""
    return yaml.safe_dump(
        {field: value},
        sort_keys=False,
        allow_unicode=True,
        width=10_000,
    ).strip()


def render_list(
    field: str,
    values: list[str],
) -> str:
    """Render a YAML list using inline syntax."""
    rendered = yaml.safe_dump(
        values,
        default_flow_style=True,
        sort_keys=False,
        allow_unicode=True,
        width=10_000,
    ).strip()

    return f"{field}: {rendered}"


def render_page(
    *,
    page_id: str,
    title: str,
    description: str,
    content_type: str,
    topics: list[str],
    components: list[str],
    prerequisites: list[str],
    next_steps: list[str],
    related_pages: list[str],
    audience: list[str],
) -> str:
    """Render the IA-defined metadata for a new page."""
    lines = [
        "---",
        render_scalar("id", page_id),
        render_scalar("title", title),
        render_scalar("description", description),
        render_scalar("content_type", content_type),
        "lifecycle_status: draft",
        render_list("topics", topics),
    ]

    if components:
        lines.append(
            render_list(
                "components",
                components,
            )
        )

    if prerequisites:
        lines.append(
            render_list(
                "prerequisites",
                prerequisites,
            )
        )

    if next_steps:
        lines.append(
            render_list(
                "next_steps",
                next_steps,
            )
        )

    if related_pages:
        lines.append(
            render_list(
                "related_pages",
                related_pages,
            )
        )

    lines.append(
        render_list(
            "audience",
            audience,
        )
    )

    lines.extend(
        [
            "---",
            "",
        ]
    )

    return "\n".join(lines)


def create_page(
    path: Path,
    content: str,
) -> None:
    """Create a new documentation page."""
    if path.exists():
        raise CreateDocPageError(
            f"Page already exists: {path}"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a Fern documentation page "
            "from IA-defined metadata."
        )
    )

    parser.add_argument(
        "--id",
        required=True,
        help="Stable documentation page ID.",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Documentation page title.",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Documentation page description.",
    )
    parser.add_argument(
        "--content-type",
        required=True,
        help="Documentation content type.",
    )
    parser.add_argument(
        "--topics",
        nargs="+",
        required=True,
        help="One or more controlled topic IDs.",
    )
    parser.add_argument(
        "--components",
        nargs="*",
        help="Controlled component IDs.",
    )
    parser.add_argument(
        "--prerequisites",
        nargs="*",
        help="Prerequisite page IDs.",
    )
    parser.add_argument(
        "--next-steps",
        nargs="*",
        help="Next-step page IDs.",
    )
    parser.add_argument(
        "--related-pages",
        nargs="*",
        help="Related page IDs.",
    )
    parser.add_argument(
        "--audience",
        nargs="+",
        required=True,
        help="One or more controlled audience values.",
    )
    parser.add_argument(
        "--path",
        required=True,
        type=Path,
        help=(
            "Repository-relative path under "
            "fern/docs/pages."
        ),
    )

    args = parser.parse_args()
    model = load_content_model()

    try:
        path = resolve_page_path(args.path)
        page_id = validate_page_id(args.id)

        title = validate_text(
            args.title,
            "title",
        )
        description = validate_text(
            args.description,
            "description",
        )

        content_type = validate_content_type(
            args.content_type
        )

        topics = validate_values(
            args.topics,
            "topics",
            allowed=model.topics,
            required=True,
        )

        components = validate_values(
            args.components,
            "components",
            allowed=model.components,
        )

        prerequisites = validate_values(
            args.prerequisites,
            "prerequisites",
        )

        next_steps = validate_values(
            args.next_steps,
            "next_steps",
        )

        related_pages = validate_values(
            args.related_pages,
            "related_pages",
        )

        audience = validate_values(
            args.audience,
            "audience",
            allowed=model.audiences,
            required=True,
        )

        content = render_page(
            page_id=page_id,
            title=title,
            description=description,
            content_type=content_type,
            topics=topics,
            components=components,
            prerequisites=prerequisites,
            next_steps=next_steps,
            related_pages=related_pages,
            audience=audience,
        )

        create_page(
            path,
            content,
        )

        update_registry()

    except CreateDocPageError as exc:
        print(
            "Could not create page:"
            f"\n\n{exc}"
        )
        return 1

    print(
        "Created: "
        f"{path.relative_to(REPO_ROOT)}"
    )
    print(
        "Updated: "
        "doc-infrastructure/page-registry.yml"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())