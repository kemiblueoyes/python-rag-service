"""Check page discovery and production mode through the validation command."""

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from rag_service.commands.documentation import validate_docs


@pytest.fixture
def pages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    root = tmp_path / "pages"
    sources = ["home.mdx", "search-answer/search-documentation.mdx"]
    paths = []
    for source in sources:
        path = root / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            (validate_docs.PUBLIC_PAGES_ROOT / source).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        paths.append(path)
    monkeypatch.setattr(validate_docs, "PUBLIC_PAGES_ROOT", root)
    # Keep the real metadata and structure validators. External tools and
    # Git-derived dates are covered by their own checks, not this command test.
    monkeypatch.setattr(
        validate_docs.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 0)),
    )
    monkeypatch.setattr(validate_docs, "validate_fern_rules", lambda: [])
    monkeypatch.setattr(validate_docs, "check_last_modified_pages", lambda paths: [])
    monkeypatch.setattr("sys.argv", ["validate_docs"])
    return paths


def test_all_pages_receive_metadata_and_structure_checks(
    pages: list[Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    metadata = Mock(wraps=validate_docs.validate_frontmatter_paths)
    structure = Mock(wraps=validate_docs.validate_structure_paths)
    monkeypatch.setattr(validate_docs, "validate_frontmatter_paths", metadata)
    monkeypatch.setattr(validate_docs, "validate_structure_paths", structure)

    validate_docs.main()

    assert metadata.call_args.args[0] == pages
    assert structure.call_args.args[0] == pages


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        ("title: Search documentation", "", "missing required field 'title'"),
        ("<Steps toc={true}>", "", "exactly one <Steps> component"),
    ],
)
def test_invalid_nested_page_stops_validation(
    pages: list[Path],
    capsys: pytest.CaptureFixture[str],
    old: str,
    new: str,
    error: str,
) -> None:
    nested = pages[1]
    content = nested.read_text(encoding="utf-8")
    assert old in content
    nested.write_text(content.replace(old, new), encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        validate_docs.main()

    assert exc.value.code == 1
    assert error in capsys.readouterr().out


@pytest.mark.parametrize("production", [False, True])
def test_draft_is_allowed_only_in_regular_mode(
    pages: list[Path], monkeypatch: pytest.MonkeyPatch, production: bool
) -> None:
    nested = pages[1]
    nested.write_text(
        nested.read_text(encoding="utf-8").replace(
            "lifecycle_status: published", "lifecycle_status: draft"
        ),
        encoding="utf-8",
    )
    if production:
        monkeypatch.setattr("sys.argv", ["validate_docs", "--production"])
        with pytest.raises(SystemExit) as exc:
            validate_docs.main()
        assert exc.value.code == 1
        validate_docs.subprocess.run.assert_not_called()
    else:
        validate_docs.main()


def test_empty_page_tree_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validate_docs, "PUBLIC_PAGES_ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["validate_docs", "--production"])

    with pytest.raises(SystemExit, match="No public documentation pages found"):
        validate_docs.main()
