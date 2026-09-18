"""Generate or validate the OpenAPI specification consumed by Fern."""

import argparse
from pathlib import Path

import yaml

from rag_service.api.app import app

OUTPUT_PATH = Path("fern/openapi.yml")

GENERATED_HEADER = """\
# GENERATED FILE — DO NOT EDIT DIRECTLY.
# Source: FastAPI application schema.
# Regenerate with:
#   uv run python -m rag_service.commands.generate_openapi
# To check if fern/openapi.yml matches the current FastAPI schema.:
#   uv run python -m rag_service.commands.generate_openapi --check

"""


def render_openapi() -> str:
    """Return the current FastAPI OpenAPI schema as YAML."""

    schema = app.openapi()

    yaml_content = yaml.safe_dump(
        schema,
        sort_keys=False,
        allow_unicode=True,
    )

    return GENERATED_HEADER + yaml_content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether fern/openapi.yml is up to date.",
    )
    args = parser.parse_args()

    generated_content = render_openapi()

    if args.check:
        if (
            not OUTPUT_PATH.exists()
            or OUTPUT_PATH.read_text(encoding="utf-8")
            != generated_content
        ):
            print(
                "fern/openapi.yml is out of date. "
                "Regenerate it with:\n"
                "uv run python -m rag_service.commands.generate_openapi"
            )
            raise SystemExit(1)

        print("fern/openapi.yml is up to date.")
        return

    OUTPUT_PATH.write_text(
        generated_content,
        encoding="utf-8",
    )

    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()