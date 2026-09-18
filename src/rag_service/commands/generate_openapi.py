"""Generate the OpenAPI specification consumed by Fern."""

from pathlib import Path

import yaml

from rag_service.api.app import app


OUTPUT_PATH = Path("fern/openapi.yml")

GENERATED_HEADER = """\
# GENERATED FILE — DO NOT EDIT DIRECTLY.
# Source: FastAPI application schema.
# Regenerate with:
#   uv run python -m rag_service.commands.generate_openapi

"""


def main() -> None:
    schema = app.openapi()

    yaml_content = yaml.safe_dump(
        schema,
        sort_keys=False,
        allow_unicode=True,
    )

    OUTPUT_PATH.write_text(
        GENERATED_HEADER + yaml_content,
        encoding="utf-8",
    )

    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()