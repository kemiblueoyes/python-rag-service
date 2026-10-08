import os
import subprocess
import sys
from pathlib import Path

CANARY = "settings-canary-sk-secret"

OPENAPI_SCRIPT = """
from rag_service.api.app import app

paths = app.openapi()["paths"]
assert "/health" in paths
assert "/v1/search" in paths
assert "/v1/answer" in paths
print("openapi-ok")
"""

LOAD_SCRIPT = """
from rag_service.config import settings

print("loaded", settings.generation_enabled)
"""

VALIDATE_URL_SCRIPT = """
from rag_service.api.app import app
from rag_service.api.startup import validate_api_configuration
from rag_service.config import settings

paths = app.openapi()["paths"]
assert "/health" in paths
assert "/v1/search" in paths
assert "/v1/answer" in paths
print("openapi-ok")
validate_api_configuration(settings)
"""


def _run(
    tmp_path: Path,
    script: str,
    *,
    env: dict[str, str] | None = None,
    dotenv: str | None = None,
    dotenv_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[str]:
    if dotenv is not None:
        (tmp_path / ".env").write_text(dotenv, encoding="utf-8")
    if dotenv_bytes is not None:
        (tmp_path / ".env").write_bytes(dotenv_bytes)

    clean = {
        "PATH": os.environ["PATH"],
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if env:
        clean.update(env)
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=clean,
        capture_output=True,
        text=True,
        check=False,
    )


def _output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def _assert_canary_hidden(result: subprocess.CompletedProcess[str]) -> str:
    output = _output(result)
    assert CANARY not in output
    assert "input_value" not in output
    assert "The above exception" not in output
    assert "During handling" not in output
    assert "loaded" not in result.stdout
    return output


def test_import_and_openapi_work_without_credentials_or_corpus(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, OPENAPI_SCRIPT)

    assert result.returncode == 0
    assert "openapi-ok" in result.stdout
    assert CANARY not in _output(result)


def test_valid_dotenv_value_is_loaded(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        LOAD_SCRIPT,
        dotenv=(
            "GENERATION_ENABLED=false\nQDRANT_URL=https://cluster.example.qdrant.io\n"
        ),
    )

    assert result.returncode == 0
    assert "loaded False" in result.stdout


def test_malformed_dotenv_statement_fails_without_using_defaults(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        LOAD_SCRIPT,
        dotenv=f'GENERATION_ENABLED="{CANARY}\nGENERATION_ENABLED=false\n',
    )

    output = _assert_canary_hidden(result)
    assert result.returncode != 0
    assert ".env" in output
    assert "line 1" in output
    assert "NAME=value" in output


def test_non_utf8_dotenv_fails_without_printing_file_bytes(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        LOAD_SCRIPT,
        dotenv_bytes=b"\xff" + CANARY.encode("ascii") + b"\n",
    )

    output = _assert_canary_hidden(result)
    assert result.returncode != 0
    assert ".env" in output
    assert "UTF-8" in output


def test_invalid_boolean_integer_and_provider_fail_in_a_fresh_process(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        LOAD_SCRIPT,
        env={
            "EMBEDDING_DIMENSION": f"12{CANARY}",
            "GENERATION_PROVIDER": f"anthropic-{CANARY}",
        },
        dotenv=f"GENERATION_ENABLED=not-a-bool-{CANARY}\n",
    )

    output = _assert_canary_hidden(result)
    assert result.returncode != 0
    assert "GENERATION_ENABLED" in output
    assert "true or false" in output
    assert "EMBEDDING_DIMENSION" in output
    assert "integer" in output
    assert "GENERATION_PROVIDER" in output
    assert "openai" in output


def test_invalid_json_collection_fails_without_printing_the_value(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        LOAD_SCRIPT,
        env={"WORDPRESS_COLLECTIONS": f"not-json-{CANARY}"},
    )

    output = _assert_canary_hidden(result)
    assert result.returncode != 0
    assert "WORDPRESS_COLLECTIONS" in output
    assert "JSON array of strings" in output


def test_malformed_qdrant_url_still_allows_openapi_and_hides_the_url(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        VALIDATE_URL_SCRIPT,
        env={"QDRANT_URL": f"http://localhost:{CANARY}"},
    )

    output = _assert_canary_hidden(result)
    assert result.returncode != 0
    assert "openapi-ok" in result.stdout
    assert "QDRANT_URL" in output
    assert "HTTP or HTTPS URL" in output
