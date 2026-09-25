"""Validate documentation frontmatter against the content model."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MODEL_PATH = REPO_ROOT / "doc-infrastructure" / "content-model.yml"

DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "doc-infrastructure" / "page-registry.yml"
)

PAGE_RELATIONSHIP_FIELDS = (
    "prerequisites",
    "next_steps",
    "related_pages",
)

@dataclass(frozen=True)
class PageRegistry:
    pages: dict[str, str]

@dataclass(frozen=True)
class ContentModel:
    required_base_fields: frozenset[str]
    content_types: dict[str, frozenset[str]]
    lifecycle_statuses: frozenset[str]
    audiences: frozenset[str]
    list_fields: frozenset[str]
    topics: frozenset[str]
    components: frozenset[str]


class FrontmatterValidationError(ValueError):
    """Raised when documentation frontmatter is invalid."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors

def load_page_registry(
    model: ContentModel,
    path: Path = DEFAULT_REGISTRY_PATH,
) -> PageRegistry:
    """Load the canonical documentation page registry."""
    if not path.is_file():
        raise FileNotFoundError(f"Page registry not found: {path}")

    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError("Page registry must contain a top-level mapping.")

    if raw.get("version") != 1:
        raise ValueError(
            "'version' in the page registry must be 1."
        )

    raw_pages = raw.get("pages")

    if not isinstance(raw_pages, list):
        raise ValueError("'pages' in the page registry must be a list.")

    pages: dict[str, str] = {}

    for index, entry in enumerate(raw_pages, start=1):
        label = f"Page registry entry #{index}"

        if not isinstance(entry, dict):
            raise ValueError(f"{label} must be a mapping.")

        page_id = entry.get("id")
        content_type = entry.get("content_type")

        if not isinstance(page_id, str) or not page_id.strip():
            raise ValueError(
                f"{label}: 'id' must be a non-empty string."
            )

        if (
            not isinstance(content_type, str)
            or not content_type.strip()
        ):
            raise ValueError(
                f"{label}: 'content_type' must be a "
                "non-empty string."
            )

        page_id = page_id.strip()
        content_type = content_type.strip()

        if page_id in pages:
            raise ValueError(
                f"{label}: duplicate page id {page_id!r}."
            )

        if content_type not in model.content_types:
            raise ValueError(
                f"{label}: unknown content_type "
                f"{content_type!r}."
            )

        pages[page_id] = content_type

    return PageRegistry(pages=pages)

def _validate_page_relationships(
    frontmatter: dict[str, Any],
    registry: PageRegistry,
    label: str,
    errors: list[str],
) -> None:
    source_id = frontmatter.get("id")

    for field in PAGE_RELATIONSHIP_FIELDS:
        values = frontmatter.get(field)

        if values is None:
            continue

        # The general list-field validation reports this error.
        if not isinstance(values, list):
            continue

        seen: set[str] = set()

        for target_id in values:
            # The general string-list validation reports this error.
            if not isinstance(target_id, str) or not target_id.strip():
                continue

            target_id = target_id.strip()

            if target_id in seen:
                errors.append(
                    f"{label}: duplicate page id {target_id!r} "
                    f"in {field!r}."
                )
                continue

            seen.add(target_id)

            if (
                isinstance(source_id, str)
                and target_id == source_id
            ):
                errors.append(
                    f"{label}: {field!r} cannot reference "
                    "the page itself."
                )

            if target_id not in registry.pages:
                errors.append(
                    f"{label}: unknown page id {target_id!r} "
                    f"in {field!r}."
                )
        
def _validate_registered_content_type(
    frontmatter: dict[str, Any],
    registry: PageRegistry,
    label: str,
    errors: list[str],
) -> None:
    """Catch canonical pages whose content types accidentally change"""
    page_id = frontmatter.get("id")
    content_type = frontmatter.get("content_type")

    if not isinstance(page_id, str):
        return

    expected = registry.pages.get(page_id)

    if expected is None:
        return

    if isinstance(content_type, str) and content_type != expected:
        errors.append(
            f"{label}: page {page_id!r} must use "
            f"content_type {expected!r}; found "
            f"{content_type!r}."
        )

def load_content_model(path: Path = DEFAULT_MODEL_PATH) -> ContentModel:
    """Load the documentation content-model contract."""
    if not path.is_file():
        raise FileNotFoundError(f"Content model not found: {path}")

    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError("Content model must contain a top-level mapping.")

    raw_content_types = raw.get("content_types")
    if not isinstance(raw_content_types, dict):
        raise ValueError("'content_types' must be a mapping.")

    content_types: dict[str, frozenset[str]] = {}

    for name, rules in raw_content_types.items():
        if not isinstance(name, str):
            raise ValueError("Every content type name must be a string.")

        if rules is None:
            rules = {}

        if not isinstance(rules, dict):
            raise ValueError(
                f"Rules for content type {name!r} must be a mapping."
            )

        required_fields = rules.get("required_fields", [])

        if not isinstance(required_fields, list) or not all(
            isinstance(field, str) for field in required_fields
        ):
            raise ValueError(
                f"'required_fields' for {name!r} must be a list of strings."
            )

        content_types[name] = frozenset(required_fields)

    return ContentModel(
        required_base_fields=_string_set(raw, "required_base_fields"),
        content_types=content_types,
        lifecycle_statuses=_string_set(raw, "lifecycle_statuses"),
        audiences=_string_set(raw, "audience"),
        list_fields=_string_set(raw, "list_fields"),
        topics=_string_set(raw, "topics"),
        components=_string_set(raw, "components"),
    )


def _string_set(raw: dict[str, Any], field: str) -> frozenset[str]:
    value = raw.get(field)

    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"'{field}' must be a list of strings.")

    return frozenset(value)


def parse_frontmatter(path: Path) -> dict[str, Any]:
    """Read YAML frontmatter from an MDX file."""
    text = path.read_text(encoding="utf-8")

    if not text.startswith("---\n"):
        raise FrontmatterValidationError(
            [f"{path}: missing YAML frontmatter."]
        )

    closing = text.find("\n---", 4)

    if closing == -1:
        raise FrontmatterValidationError(
            [f"{path}: frontmatter is not closed with '---'."]
        )

    raw_frontmatter = text[4:closing]

    try:
        data = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError as exc:
        raise FrontmatterValidationError(
            [f"{path}: invalid YAML frontmatter: {exc}"]
        ) from exc

    if not isinstance(data, dict):
        raise FrontmatterValidationError(
            [f"{path}: frontmatter must contain a mapping."]
        )

    return data


def validate_document(
    path: Path,
    model: ContentModel,
    registry: PageRegistry,
) -> list[str]:
    """Return frontmatter validation errors for one MDX page."""
    try:
        frontmatter = parse_frontmatter(path)
    except FrontmatterValidationError as exc:
        return exc.errors

    errors: list[str] = []
    label = str(path)

    _validate_required_fields(
        frontmatter,
        model.required_base_fields,
        label,
        errors,
    )

    content_type = frontmatter.get("content_type")

    if isinstance(content_type, str):
        if content_type not in model.content_types:
            errors.append(
                f"{label}: unknown content_type {content_type!r}."
            )
        else:
            _validate_required_fields(
                frontmatter,
                model.content_types[content_type],
                label,
                errors,
            )

    lifecycle_status = frontmatter.get("lifecycle_status")

    if isinstance(lifecycle_status, str):
        if lifecycle_status not in model.lifecycle_statuses:
            errors.append(
                f"{label}: unknown lifecycle_status "
                f"{lifecycle_status!r}."
            )

    _validate_non_empty_strings(
        frontmatter,
        (
            "id",
            "title",
            "subtitle",
            "description",
            "content_type",
            "lifecycle_status",
        ),
        label,
        errors,
    )

    for field in model.list_fields:
        if field in frontmatter:
            _validate_string_list(
                frontmatter[field],
                field,
                label,
                errors,
            )

    audience = frontmatter.get("audience")

    if isinstance(audience, list):
        if not audience:
            errors.append(
                f"{label}: 'audience' must contain at least one value."
            )

        for audience_value in audience:
            if (
                isinstance(audience_value, str)
                and audience_value not in model.audiences
            ):
                errors.append(
                    f"{label}: unknown audience {audience_value!r}."
                )

    topics = frontmatter.get("topics")

    if isinstance(topics, list):
        if not topics:
            errors.append(
                f"{label}: 'topics' must contain at least one value."
            )

        for topic in topics:
            if isinstance(topic, str) and topic not in model.topics:
                errors.append(
                    f"{label}: unknown topic {topic!r}."
                )

    components = frontmatter.get("components")

    if isinstance(components, list):
        for component in components:
            if (
                isinstance(component, str)
                and component not in model.components
            ):
                errors.append(
                    f"{label}: unknown component {component!r}."
                )

    _validate_last_modified(
        frontmatter.get("last_modified"),
        label,
        errors,
    )

    _validate_registered_content_type(
        frontmatter,
        registry,
        label,
        errors,
    )

    _validate_page_relationships(
        frontmatter,
        registry,
        label,
        errors,
    )

    return errors


def _validate_required_fields(
    frontmatter: dict[str, Any],
    required_fields: frozenset[str],
    label: str,
    errors: list[str],
) -> None:
    for field in sorted(required_fields):
        if field not in frontmatter:
            errors.append(
                f"{label}: missing required field {field!r}."
            )


def _validate_non_empty_strings(
    frontmatter: dict[str, Any],
    fields: tuple[str, ...],
    label: str,
    errors: list[str],
) -> None:
    for field in fields:
        if field not in frontmatter:
            continue

        value = frontmatter[field]

        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"{label}: {field!r} must be a non-empty string."
            )


def _validate_string_list(
    value: Any,
    field: str,
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append(
            f"{label}: {field!r} must be a list."
        )
        return

    for item in value:
        if not isinstance(item, str) or not item.strip():
            errors.append(
                f"{label}: every value in {field!r} must be "
                "a non-empty string."
            )


def _validate_last_modified(
    value: Any,
    label: str,
    errors: list[str],
) -> None:
    if value is None:
        return

    # PyYAML converts unquoted YYYY-MM-DD values into datetime.date.
    if isinstance(value, date):
        return

    if isinstance(value, str):
        try:
            date.fromisoformat(value)
        except ValueError:
            pass
        else:
            return

    errors.append(
        f"{label}: 'last_modified' must use YYYY-MM-DD."
    )


def validate_paths(
    paths: list[Path],
    model: ContentModel,
    registry: PageRegistry,
) -> list[str]:
    """Validate multiple pages and check for duplicate page ids."""
    errors: list[str] = []
    ids: dict[str, Path] = {}

    for path in paths:
        document_errors = validate_document(path, model, registry)
        errors.extend(document_errors)

        if document_errors:
            continue

        frontmatter = parse_frontmatter(path)
        page_id = frontmatter["id"]

        if not isinstance(page_id, str):
            continue

        if page_id in ids:
            errors.append(
                f"{path}: duplicate id {page_id!r}; "
                f"already used by {ids[page_id]}."
            )
        else:
            ids[page_id] = path

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate documentation MDX frontmatter."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="MDX files or directories to validate.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Path to the content-model YAML contract.",
    )

    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Path to the documentation page registry.",
    )

    args = parser.parse_args()
    model = load_content_model(args.model)
    registry = load_page_registry(
        model,
        args.registry,
    )

    mdx_paths: list[Path] = []

    for path in args.paths:
        if path.is_dir():
            mdx_paths.extend(sorted(path.rglob("*.mdx")))
        elif path.suffix == ".mdx":
            mdx_paths.append(path)
        else:
            print(f"Skipping non-MDX path: {path}")

    errors = validate_paths(mdx_paths, model,registry)

    if errors:
        print("Frontmatter validation failed:\n")

        for error in errors:
            print(f"- {error}")

        return 1

    print(f"Frontmatter validation passed for {len(mdx_paths)} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())