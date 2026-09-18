"""Run documentation validation checks."""

import subprocess
import sys


def main() -> None:
    """Run all documentation validation checks."""

    print("Checking generated OpenAPI specification...")
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