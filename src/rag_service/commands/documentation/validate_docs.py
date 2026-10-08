"""Run documentation validation checks."""

import argparse
import subprocess
import sys
from pathlib import Path

from rag_service.commands.documentation.update_last_modified import (
    authored_pages,
)
from rag_service.commands.documentation.update_last_modified import (
    check_pages as check_last_modified_pages,
)
from rag_service.commands.documentation.validate_doc_structure import (
    validate_paths as validate_structure_paths,
)
from rag_service.commands.documentation.validate_fern_rules import (
    validate_fern_rules,
)
from rag_service.commands.documentation.validate_frontmatter import (
    FrontmatterValidationError,
    load_content_model,
    load_page_registry,
    parse_frontmatter,
)
from rag_service.commands.documentation.validate_frontmatter import (
    validate_paths as validate_frontmatter_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[4]

TEST_TEMPLATE_DIR = (
    REPO_ROOT
    / "doc-infrastructure"
    / "templates"
    / "test-templates"
)

PAGE_FIXTURES = [
    TEST_TEMPLATE_DIR / "overview_Home.mdx",
    TEST_TEMPLATE_DIR / "overview_Search-and-answer-overview.mdx",
    TEST_TEMPLATE_DIR / "how-to_Search-documentation.mdx",
    TEST_TEMPLATE_DIR / "tutorial_Build-inspect-your-first-doc-index.mdx",
    TEST_TEMPLATE_DIR / "explanation_Retrieval-pipeline.mdx",
    TEST_TEMPLATE_DIR / "general-reference_Configuration-reference.mdx",
    TEST_TEMPLATE_DIR / "general-reference_Glossary.mdx",
    TEST_TEMPLATE_DIR / "evaluation-results_Recorded-evaluation-results.mdx",
    TEST_TEMPLATE_DIR / "release-note_Hybrid-retrieval.mdx",
]

PUBLIC_PAGES_ROOT = REPO_ROOT / "fern" / "docs" / "pages"


def validate_production_pages(paths: list[Path]) -> list[str]:
    """Reject unpublished content in the production Fern source tree.

    Keep drafts, review pages, and archives outside fern/docs/pages.
    Check all page sources, including pages omitted from navigation.
    """
    errors: list[str] = []
    for path in paths:
        try:
            frontmatter = parse_frontmatter(path)
        except FrontmatterValidationError as exc:
            errors.extend(exc.errors)
            continue

        status = frontmatter.get("lifecycle_status")
        if status not in ("published", "deprecated"):
            errors.append(
                f"{path}: production pages must use lifecycle_status "
                f"'published' or 'deprecated'; found {status!r}. "
                "Move drafts, review pages, and archives outside fern/docs/pages."
            )
        if "draft" in frontmatter and frontmatter["draft"] is not False:
            errors.append(f"{path}: production pages cannot set Fern 'draft'.")

    return errors


def main() -> None:
    """Run all documentation validation checks."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--production",
        action="store_true",
        help="Require every page in fern/docs/pages to be publishable.",
    )
    args = parser.parse_args()
    public_pages = sorted(PUBLIC_PAGES_ROOT.rglob("*.mdx"))
    if not public_pages:
        raise SystemExit("No public documentation pages found.")

    print(f"Validating {len(public_pages)} documentation page(s).")

    if args.production:
        production_errors = validate_production_pages(public_pages)
        if production_errors:
            print("Production lifecycle validation failed:")
            for error in production_errors:
                print(f"- {error}")
            raise SystemExit(1)
        print("Production lifecycle validation passed.")

    print("Checking documentation page registry...")

    registry_check = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_service.commands.documentation.update_page_registry",
            "--check",
        ],
        check=False,
    )

    if registry_check.returncode != 0:
        raise SystemExit(registry_check.returncode)

    print("Checking documentation frontmatter and content model...")

    model = load_content_model()
    registry = load_page_registry(model)

    frontmatter_errors = validate_frontmatter_paths(
        public_pages,
        model,
        registry,
    )

    if frontmatter_errors:
        print("\nFrontmatter validation failed:")

        for error in frontmatter_errors:
            print(f"- {error}")

        raise SystemExit(1)

    print("Frontmatter validation passed.")

    print("\nChecking content-type structure...")

    structure_errors = validate_structure_paths(
        public_pages,
    )

    if structure_errors:
        print("\nDocumentation structure validation failed:")

        for error in structure_errors:
            print(f"- {error}")

        raise SystemExit(1)

    print("Documentation structure validation passed.")

    print("\nChecking Fern/platform rules...")

    fern_rule_errors = validate_fern_rules()

    if fern_rule_errors:
        print("\nFern/platform validation failed:")

        for error in fern_rule_errors:
            print(f"- {error}")

        raise SystemExit(1)

    print("Fern/platform validation passed.")

    print("\nLinting Markdown and MDX...")

    try:
        subprocess.run(
            ["npm", "run", "lint:docs"],
            check=True,
        )
    except FileNotFoundError:
        print(
            "npm was not found. Install Node.js and the "
            "documentation lint dependencies before running validation."
        )
        raise SystemExit(1) from None

    print("Markdown/MDX linting passed.")

    print("\nChecking generated last_modified metadata...")

    last_modified_errors = check_last_modified_pages(
        authored_pages()
    )

    if last_modified_errors:
        print("\nlast_modified validation failed:")

        for error in last_modified_errors:
            print(f"- {error}")

        print(
            "\nRun this command to update authored pages:\n"
            "uv run python -m "
            "rag_service.commands.documentation.update_last_modified"
        )

        raise SystemExit(1)

    print("Authored-page last_modified metadata is current.")

    print("\nChecking generated glossary and terminology artifacts...")

    subprocess.run(
        [
            sys.executable,
            "scripts/generate_glossary.py",
            "--check",
        ],
        check=True,
    )

    print("Generated glossary and terminology artifacts are current.")

    print("\nChecking prose and terminology with Vale...")

    try:
        subprocess.run(
            ["vale", "fern/docs/pages"],
            check=True,
        )
    except FileNotFoundError:
        print(
            "Vale was not found. Install Vale before running "
            "documentation validation."
        )
        raise SystemExit(1) from None

    print("Vale validation passed.")

    print("\nChecking generated OpenAPI specification...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_service.commands.generate_openapi",
            "--check",
        ],
        check=True,
    )

    print("\nChecking Fern configuration and API definition...")
    try:
        subprocess.run(
            ["fern", "check"],
            check=True,
        )
    except FileNotFoundError:
        print(
            "Fern CLI was not found. "
            "Install or configure Fern before running documentation validation."
        )
        raise SystemExit(1) from None

    print("\nDocumentation validation passed.")


if __name__ == "__main__":
    main()
