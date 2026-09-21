"""Validate Fern-specific documentation authoring rules."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

from rag_service.commands.documentation.validate_frontmatter import (
    FrontmatterValidationError,
    parse_frontmatter,
)

REPO_ROOT = Path(__file__).resolve().parents[4]

PUBLIC_DOCS_ROOT = (
    REPO_ROOT
    / "fern"
    / "docs"
    / "pages"
)

DOCS_CONFIG_PATH = REPO_ROOT / "fern" / "docs.yml"

FILENAME_PATTERN = re.compile(
    r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
)

MARKDOWN_LINK_PATTERN = re.compile(
    r"(?<!!)\[[^\]]+\]\(([^)]+)\)"
)

HREF_PATTERN = re.compile(
    r"""\bhref\s*=\s*["']([^"']+)["']"""
)

PAGE_SUFFIXES = {
    "",
    ".md",
    ".mdx",
}


def validate_public_docs_tree(root: Path) -> list[str]:
    """Validate Fern rules across the public documentation tree."""
    errors: list[str] = []

    if not root.is_dir():
        return [
            f"Public documentation directory not found: {root}"
        ]

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix == ".md":
            errors.append(
                f"{path}: public authored documentation "
                "must use .mdx, not .md."
            )
            continue

        if path.suffix != ".mdx":
            continue

        errors.extend(
            validate_public_page(path)
        )

    return errors


def validate_public_page(path: Path) -> list[str]:
    """Validate Fern-specific rules for one public MDX page."""
    errors: list[str] = []

    _validate_filename(
        path,
        errors,
    )

    _validate_platform_frontmatter(
        path,
        errors,
    )

    _validate_internal_links(
        path,
        errors,
    )

    return errors


def _validate_filename(
    path: Path,
    errors: list[str],
) -> None:
    if not FILENAME_PATTERN.fullmatch(path.stem):
        errors.append(
            f"{path}: MDX filename must use lowercase "
            "kebab case with no ordering prefix."
        )


def _validate_platform_frontmatter(
    path: Path,
    errors: list[str],
) -> None:
    try:
        frontmatter = parse_frontmatter(path)
    except FrontmatterValidationError:
        # Frontmatter validity belongs to validate_frontmatter.
        return

    if "slug" in frontmatter:
        errors.append(
            f"{path}: do not use frontmatter 'slug'; "
            "let docs.yml control URL structure."
        )

    if "last-updated" in frontmatter:
        errors.append(
            f"{path}: use 'last_modified' instead of "
            "Fern 'last-updated'."
        )


def _validate_internal_links(
    path: Path,
    errors: list[str],
) -> None:
    text = path.read_text(encoding="utf-8")
    searchable = _remove_fenced_code(text)

    targets: list[str] = []

    targets.extend(
        match.group(1)
        for match in MARKDOWN_LINK_PATTERN.finditer(
            searchable
        )
    )

    targets.extend(
        match.group(1)
        for match in HREF_PATTERN.finditer(
            searchable
        )
    )

    for raw_target in targets:
        target = _extract_link_target(raw_target)

        if target is None:
            continue

        if _is_invalid_page_link(target):
            errors.append(
                f"{path}: internal page link {target!r} "
                "must use a published '/...' path or "
                "Fern 'api:' syntax."
            )


def _extract_link_target(
    raw_target: str,
) -> str | None:
    target = raw_target.strip()

    if not target:
        return None

    if target.startswith("<"):
        closing = target.find(">")

        if closing == -1:
            return target

        return target[1:closing].strip()

    # Markdown links may include an optional title:
    #
    # (/path "Title")
    #
    # Only the first value is the URL.
    return target.split(maxsplit=1)[0]


def _is_invalid_page_link(target: str) -> bool:
    lowered = target.casefold()

    if lowered.startswith(
        (
            "http://",
            "https://",
            "mailto:",
            "tel:",
            "api:",
            "#",
        )
    ):
        return False

    path_part = (
        target.split("#", maxsplit=1)[0]
        .split("?", maxsplit=1)[0]
    )

    suffix = Path(path_part).suffix.casefold()

    # A Markdown source path is never the published URL.
    if suffix in {".md", ".mdx"}:
        return True

    # Root-relative links are the normal Fern page-link form.
    if path_part.startswith("/"):
        return False

    # Relative paths with no file extension are almost certainly
    # filesystem-relative page links such as ../authentication.
    if path_part.startswith(("./", "../")):
        return suffix in PAGE_SUFFIXES

    # A bare internal path such as:
    #
    # get-started/authentication
    #
    # is also not our published-path convention.
    if suffix == "":
        return True

    # Allow relative links to non-page files such as images,
    # downloads, YAML examples, and other assets.
    return False


def _remove_fenced_code(text: str) -> str:
    """Remove fenced code so examples are not treated as real links."""
    lines: list[str] = []
    fence: str | None = None

    for line in text.splitlines():
        stripped = line.lstrip()

        if fence is not None:
            if stripped.startswith(fence):
                fence = None

            lines.append("")
            continue

        if stripped.startswith("```"):
            fence = "```"
            lines.append("")
            continue

        if stripped.startswith("~~~"):
            fence = "~~~"
            lines.append("")
            continue

        lines.append(line)

    return "\n".join(lines)


def validate_docs_config(
    path: Path = DOCS_CONFIG_PATH,
) -> list[str]:
    """Validate project-specific Fern docs.yml rules."""
    if not path.is_file():
        return [f"Fern docs config not found: {path}"]

    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        return [
            f"{path}: docs.yml must contain a top-level mapping."
        ]

    navigation: Any = data.get("navigation")

    if not isinstance(navigation, list) or not navigation:
        return [
            f"{path}: use explicit docs.yml navigation "
            "for the documentation IA."
        ]

    return []


def validate_fern_rules(
    root: Path = PUBLIC_DOCS_ROOT,
    docs_config: Path = DOCS_CONFIG_PATH,
) -> list[str]:
    """Run all project-specific Fern/platform checks."""
    errors = validate_public_docs_tree(root)

    errors.extend(
        validate_docs_config(docs_config)
    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Fern/platform documentation rules."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PUBLIC_DOCS_ROOT,
        help="Public Fern documentation directory.",
    )
    parser.add_argument(
        "--docs-config",
        type=Path,
        default=DOCS_CONFIG_PATH,
        help="Fern docs.yml path.",
    )

    args = parser.parse_args()

    errors = validate_fern_rules(
        root=args.root,
        docs_config=args.docs_config,
    )

    if errors:
        print("Fern/platform validation failed:\n")

        for error in errors:
            print(f"- {error}")

        return 1

    print("Fern/platform validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())