"""Validate documentation body structure by content type."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from rag_service.commands.documentation.validate_frontmatter import (
    FrontmatterValidationError,
    parse_frontmatter,
)


@dataclass(frozen=True)
class Heading:
    """An H2 heading found in an MDX page."""

    text: str
    line: int
    inside_steps: bool


@dataclass(frozen=True)
class DocumentStructure:
    """Structural landmarks extracted from an MDX body."""

    h1_lines: tuple[int, ...]
    h2_headings: tuple[Heading, ...]
    steps_open_lines: tuple[int, ...]
    steps_close_lines: tuple[int, ...]


def extract_body(path: Path) -> str:
    """Return MDX body content without YAML frontmatter."""
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

    return text[closing + 4 :].lstrip("\n")


def extract_structure(body: str) -> DocumentStructure:
    """Extract headings and Steps components from MDX body."""
    h1_lines: list[int] = []
    headings: list[Heading] = []
    steps_open_lines: list[int] = []
    steps_close_lines: list[int] = []

    fence: str | None = None
    inside_steps = False

    for line_number, line in enumerate(
        body.splitlines(),
        start=1,
    ):
        stripped = line.strip()

        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue

        if stripped.startswith("```"):
            fence = "```"
            continue

        if stripped.startswith("~~~"):
            fence = "~~~"
            continue

        if re.match(r"^<Steps(?:\s|>)", stripped):
            steps_open_lines.append(line_number)
            inside_steps = True
            continue

        if stripped.startswith("</Steps>"):
            steps_close_lines.append(line_number)
            inside_steps = False
            continue

        if re.match(r"^#(?!#)\s+", stripped):
            h1_lines.append(line_number)
            continue

        match = re.match(
            r"^##(?!#)\s+(.+?)\s*$",
            stripped,
        )

        if match:
            headings.append(
                Heading(
                    text=match.group(1).strip(),
                    line=line_number,
                    inside_steps=inside_steps,
                )
            )

    return DocumentStructure(
        h1_lines=tuple(h1_lines),
        h2_headings=tuple(headings),
        steps_open_lines=tuple(steps_open_lines),
        steps_close_lines=tuple(steps_close_lines),
    )


def validate_document_structure(path: Path) -> list[str]:
    """Return structural validation errors for one MDX page."""
    try:
        frontmatter = parse_frontmatter(path)
        body = extract_body(path)
    except FrontmatterValidationError as exc:
        return exc.errors

    content_type = frontmatter.get("content_type")

    if not isinstance(content_type, str):
        return [
            f"{path}: cannot validate body structure without "
            "a valid content_type."
        ]

    structure = extract_structure(body)
    errors: list[str] = []
    label = str(path)

    if structure.h1_lines:
        errors.append(
            f"{label}: body must not contain an H1 heading; "
            "Fern renders the page title."
        )

    validators = {
        "overview": _validate_overview,
        "how_to": _validate_how_to,
        "tutorial": _validate_tutorial,
        "explanation": _validate_explanation,
        "general_reference": _validate_general_reference,
        "eval_results": _validate_eval_results,
        "release_note": _validate_release_note,
    }

    validator = validators.get(content_type)

    # API reference pages are generated from OpenAPI rather than
    # authored with these MDX page templates.
    if validator is not None:
        validator(
            structure,
            label,
            errors,
        )

    return errors


def _outside_headings(
    structure: DocumentStructure,
) -> tuple[Heading, ...]:
    return tuple(
        heading
        for heading in structure.h2_headings
        if not heading.inside_steps
    )


def _heading_map(
    structure: DocumentStructure,
) -> dict[str, Heading]:
    return {
        heading.text.casefold(): heading
        for heading in _outside_headings(structure)
    }


def _require_heading(
    headings: dict[str, Heading],
    name: str,
    label: str,
    errors: list[str],
) -> None:
    if name.casefold() not in headings:
        errors.append(
            f"{label}: missing required H2 heading {name!r}."
        )


def _validate_steps_component(
    structure: DocumentStructure,
    label: str,
    errors: list[str],
) -> tuple[int, int] | None:
    if len(structure.steps_open_lines) != 1:
        errors.append(
            f"{label}: page must contain exactly one "
            "<Steps> component."
        )
        return None

    if len(structure.steps_close_lines) != 1:
        errors.append(
            f"{label}: page must contain exactly one "
            "</Steps> closing tag."
        )
        return None

    start = structure.steps_open_lines[0]
    end = structure.steps_close_lines[0]

    if start >= end:
        errors.append(
            f"{label}: <Steps> must close after it opens."
        )
        return None

    return start, end


def _require_order(
    headings: dict[str, Heading],
    names: tuple[str, ...],
    label: str,
    errors: list[str],
) -> None:
    existing = [
        headings[name.casefold()]
        for name in names
        if name.casefold() in headings
    ]

    for first, second in zip(
        existing,
        existing[1:],
        strict=False,
    ):
        if first.line >= second.line:
            errors.append(
                f"{label}: {first.text!r} must appear before "
                f"{second.text!r}."
            )


def _validate_overview(
    structure: DocumentStructure,
    label: str,
    errors: list[str],
) -> None:
    headings = _heading_map(structure)

    _require_heading(
        headings,
        "Key capabilities",
        label,
        errors,
    )
    _require_heading(
        headings,
        "Next steps",
        label,
        errors,
    )

    _require_order(
        headings,
        (
            "Key capabilities",
            "Common use cases",
            "Next steps",
            "Related pages",
        ),
        label,
        errors,
    )


def _validate_how_to(
    structure: DocumentStructure,
    label: str,
    errors: list[str],
) -> None:
    headings = _heading_map(structure)

    for forbidden in ("Goal", "Steps"):
        if forbidden.casefold() in headings:
            errors.append(
                f"{label}: how-to pages must not use an "
                f"H2 {forbidden!r} heading."
            )

    steps = _validate_steps_component(
        structure,
        label,
        errors,
    )

    if steps is None:
        return

    steps_start, steps_end = steps

    prerequisites = headings.get("prerequisites")

    if (
        prerequisites is not None
        and prerequisites.line >= steps_start
    ):
        errors.append(
            f"{label}: 'Prerequisites' must appear before "
            "<Steps>."
        )

    for name in (
        "Verification",
        "Next steps",
        "Related pages",
    ):
        heading = headings.get(name.casefold())

        if heading is not None and heading.line <= steps_end:
            errors.append(
                f"{label}: {name!r} must appear after "
                "</Steps>."
            )

    _require_order(
        headings,
        (
            "Verification",
            "Next steps",
            "Related pages",
        ),
        label,
        errors,
    )


def _validate_tutorial(
    structure: DocumentStructure,
    label: str,
    errors: list[str],
) -> None:
    headings = _heading_map(structure)

    for name in (
        "Prerequisites",
        "What you learned",
        "Next steps",
    ):
        _require_heading(
            headings,
            name,
            label,
            errors,
        )

    steps = _validate_steps_component(
        structure,
        label,
        errors,
    )

    if steps is None:
        return

    steps_start, steps_end = steps

    prerequisites = headings.get("prerequisites")
    learned = headings.get("what you learned")
    next_steps = headings.get("next steps")

    if (
        prerequisites is not None
        and prerequisites.line >= steps_start
    ):
        errors.append(
            f"{label}: 'Prerequisites' must appear before "
            "<Steps>."
        )

    if learned is not None and learned.line <= steps_end:
        errors.append(
            f"{label}: 'What you learned' must appear after "
            "</Steps>."
        )

    if next_steps is not None and learned is not None:
        if next_steps.line <= learned.line:
            errors.append(
                f"{label}: 'Next steps' must appear after "
                "'What you learned'."
            )

    _require_order(
        headings,
        (
            "What you learned",
            "Next steps",
            "Related pages",
        ),
        label,
        errors,
    )


def _validate_explanation(
    structure: DocumentStructure,
    label: str,
    errors: list[str],
) -> None:
    headings = _heading_map(structure)

    _require_heading(
        headings,
        "Next steps",
        label,
        errors,
    )
    _require_heading(
        headings,
        "Related pages",
        label,
        errors,
    )

    semantic_headings = [
        heading
        for heading in _outside_headings(structure)
        if heading.text.casefold()
        not in {
            "next steps",
            "related pages",
        }
    ]

    if not semantic_headings:
        errors.append(
            f"{label}: explanation pages must contain at "
            "least one semantic H2 section."
        )

    _require_order(
        headings,
        (
            "Next steps",
            "Related pages",
        ),
        label,
        errors,
    )


def _validate_general_reference(
    structure: DocumentStructure,
    label: str,
    errors: list[str],
) -> None:
    if not _outside_headings(structure):
        errors.append(
            f"{label}: general reference pages must contain "
            "at least one H2 reference section."
        )


def _validate_eval_results(
    structure: DocumentStructure,
    label: str,
    errors: list[str],
) -> None:
    headings = _heading_map(structure)

    for name in (
        "Evaluation dataset",
        "Findings",
        "Limitations",
    ):
        _require_heading(
            headings,
            name,
            label,
            errors,
        )

    result_headings = [
        heading
        for heading in _outside_headings(structure)
        if (
            heading.text.casefold() == "results"
            or heading.text.casefold().endswith(" results")
        )
    ]

    if not result_headings:
        errors.append(
            f"{label}: evaluation-results pages must contain "
            "at least one H2 results section."
        )

    dataset = headings.get("evaluation dataset")
    findings = headings.get("findings")
    limitations = headings.get("limitations")

    if dataset is not None:
        for result_heading in result_headings:
            if result_heading.line <= dataset.line:
                errors.append(
                    f"{label}: results sections must appear "
                    "after 'Evaluation dataset'."
                )

    if findings is not None:
        for result_heading in result_headings:
            if result_heading.line >= findings.line:
                errors.append(
                    f"{label}: results sections must appear "
                    "before 'Findings'."
                )

    if (
        findings is not None
        and limitations is not None
        and findings.line >= limitations.line
    ):
        errors.append(
            f"{label}: 'Findings' must appear before "
            "'Limitations'."
        )

    _require_order(
        headings,
        (
            "Limitations",
            "Next steps",
            "Related pages",
        ),
        label,
        errors,
    )


def _validate_release_note(
    structure: DocumentStructure,
    label: str,
    errors: list[str],
) -> None:
    headings = _heading_map(structure)

    _require_heading(
        headings,
        "What's changed",
        label,
        errors,
    )
    _require_heading(
        headings,
        "Related documentation",
        label,
        errors,
    )

    _require_order(
        headings,
        (
            "What's changed",
            "Breaking changes",
            "Upgrade or migration",
            "Known issues",
            "Related documentation",
        ),
        label,
        errors,
    )


def validate_paths(paths: list[Path]) -> list[str]:
    """Validate body structure for multiple MDX pages."""
    errors: list[str] = []

    for path in paths:
        errors.extend(
            validate_document_structure(path)
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate documentation body structure."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="MDX files or directories to validate.",
    )

    args = parser.parse_args()

    mdx_paths: list[Path] = []

    for path in args.paths:
        if path.is_dir():
            mdx_paths.extend(
                sorted(path.rglob("*.mdx"))
            )
        elif path.suffix == ".mdx":
            mdx_paths.append(path)

    errors = validate_paths(mdx_paths)

    if errors:
        print("Documentation structure validation failed:\n")

        for error in errors:
            print(f"- {error}")

        return 1

    print(
        "Documentation structure validation passed for "
        f"{len(mdx_paths)} page(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())