"""Run documentation validation checks."""

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
    load_content_model,
    load_page_registry,
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
    TEST_TEMPLATE_DIR / "evaluation-results_Current-evaluation-results.mdx",
    TEST_TEMPLATE_DIR / "release-note_Hybrid-retrieval.mdx",
]

PUBLIC_PAGES = [
    REPO_ROOT / "fern" / "docs" / "pages" / "home.mdx",
]

def main() -> None:
    """Run all documentation validation checks."""

    print("Checking documentation frontmatter and content model...")

    model = load_content_model()
    registry = load_page_registry(model)

    frontmatter_errors = validate_frontmatter_paths(
        PUBLIC_PAGES,
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
        PUBLIC_PAGES,
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