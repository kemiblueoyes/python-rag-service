from pathlib import Path

import pytest

from scripts import generate_glossary


def write_glossary(
    tmp_path: Path,
    content: str,
) -> Path:
    path = tmp_path / "glossary.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_renders_valid_glossary(tmp_path: Path) -> None:
    source = write_glossary(
        tmp_path,
        """
version: 1

terms:
  - id: semantic-search
    term: Semantic search
    definition: Search based on meaning.

  - id: hybrid-search
    term: Hybrid search
    definition: Combines semantic and lexical search.
    example: Combines vector search and BM25.
    aliases:
      - Hybrid retrieval
    related_terms:
      - semantic-search
""",
    )

    terms = generate_glossary.load_glossary(source)
    result = generate_glossary.render_glossary(terms)

    assert "id: Gloss" in result
    assert "content_type: general_reference" in result
    assert "max-toc-depth: 3" in result

    assert result.index("### Hybrid search") < result.index(
        "### Semantic search"
    )

    assert "#### Example" in result
    assert "**Also known as:** Hybrid retrieval" in result
    assert (
        "**Related terms:** "
        "[Semantic search](#semantic-search)"
        in result
    )


def test_renders_vale_vocabulary(
    tmp_path: Path,
) -> None:
    source = write_glossary(
        tmp_path,
        """
version: 1

terms:
  - id: hybrid-search
    term: Hybrid search
    definition: Combines retrieval methods.
    aliases:
      - Hybrid retrieval
""",
    )

    terms = generate_glossary.load_glossary(source)
    result = generate_glossary.render_vale_vocabulary(
        terms,
        ["Pydantic", "pytest"],
    )

    assert result == (
        "Hybrid retrieval\n"
        "Hybrid search\n"
        "Pydantic\n"
        "pytest\n"
    )


def test_vale_vocabulary_orders_case_variants_deterministically(
    tmp_path: Path,
) -> None:
    source = write_glossary(
        tmp_path,
        """
version: 1

terms:
  - id: reranking
    term: Reranking
    definition: A second ranking pass.
""",
    )

    terms = generate_glossary.load_glossary(source)
    result = generate_glossary.render_vale_vocabulary(
        terms,
        ["reranking"],
    )

    assert result == (
        "Reranking\n"
        "reranking\n"
    )


def test_rejects_unknown_related_term(
    tmp_path: Path,
) -> None:
    source = write_glossary(
        tmp_path,
        """
version: 1

terms:
  - id: hybrid-search
    term: Hybrid search
    definition: Combines retrieval methods.
    related_terms:
      - does-not-exist
""",
    )

    with pytest.raises(
        generate_glossary.GlossaryValidationError,
        match="does not exist",
    ):
        generate_glossary.load_glossary(source)


def test_rejects_duplicate_id(
    tmp_path: Path,
) -> None:
    source = write_glossary(
        tmp_path,
        """
version: 1

terms:
  - id: semantic-search
    term: Semantic search
    definition: Search based on meaning.

  - id: semantic-search
    term: Another term
    definition: Another definition.
""",
    )

    with pytest.raises(
        generate_glossary.GlossaryValidationError,
        match="duplicate id",
    ):
        generate_glossary.load_glossary(source)


def test_rejects_duplicate_canonical_term(
    tmp_path: Path,
) -> None:
    source = write_glossary(
        tmp_path,
        """
version: 1

terms:
  - id: semantic-search
    term: Semantic search
    definition: First definition.

  - id: another-search
    term: semantic SEARCH
    definition: Second definition.
""",
    )

    with pytest.raises(
        generate_glossary.GlossaryValidationError,
        match="duplicate canonical term",
    ):
        generate_glossary.load_glossary(source)


def test_rejects_invalid_id(
    tmp_path: Path,
) -> None:
    source = write_glossary(
        tmp_path,
        """
version: 1

terms:
  - id: Bad_ID
    term: Bad ID
    definition: Test definition.
""",
    )

    with pytest.raises(
        generate_glossary.GlossaryValidationError,
        match="lowercase kebab-case",
    ):
        generate_glossary.load_glossary(source)


def test_rejects_duplicate_alias(
    tmp_path: Path,
) -> None:
    source = write_glossary(
        tmp_path,
        """
version: 1

terms:
  - id: reciprocal-rank-fusion
    term: Reciprocal rank fusion
    definition: Combines ranked result lists.
    aliases:
      - RRF
      - rrf
""",
    )

    with pytest.raises(
        generate_glossary.GlossaryValidationError,
        match="duplicate alias",
    ):
        generate_glossary.load_glossary(source)


def test_rejects_self_reference(
    tmp_path: Path,
) -> None:
    source = write_glossary(
        tmp_path,
        """
version: 1

terms:
  - id: hybrid-search
    term: Hybrid search
    definition: Combines retrieval methods.
    related_terms:
      - hybrid-search
""",
    )

    with pytest.raises(
        generate_glossary.GlossaryValidationError,
        match="cannot reference itself",
    ):
        generate_glossary.load_glossary(source)


def test_write_if_changed_reports_status(
    tmp_path: Path,
) -> None:
    output = tmp_path / "generated.txt"

    assert (
        generate_glossary.write_if_changed(
            output,
            "first\n",
        )
        == "New"
    )

    assert (
        generate_glossary.write_if_changed(
            output,
            "first\n",
        )
        == "Unchanged"
    )

    assert (
        generate_glossary.write_if_changed(
            output,
            "second\n",
        )
        == "Updated"
    )

    assert output.read_text(
        encoding="utf-8"
    ) == "second\n"

def test_check_outputs_passes_when_files_are_current(
    tmp_path: Path,
) -> None:
    glossary_path = tmp_path / "glossary.mdx"
    vale_path = tmp_path / "accept.txt"

    glossary_path.write_text(
        "generated glossary\n",
        encoding="utf-8",
    )
    vale_path.write_text(
        "generated vocabulary\n",
        encoding="utf-8",
    )

    errors = generate_glossary.check_outputs(
        "generated glossary\n",
        "generated vocabulary\n",
        glossary_path=glossary_path,
        vale_path=vale_path,
    )

    assert errors == []


def test_check_outputs_detects_stale_file(
    tmp_path: Path,
) -> None:
    glossary_path = tmp_path / "glossary.mdx"
    vale_path = tmp_path / "accept.txt"

    glossary_path.write_text(
        "old glossary\n",
        encoding="utf-8",
    )
    vale_path.write_text(
        "generated vocabulary\n",
        encoding="utf-8",
    )

    errors = generate_glossary.check_outputs(
        "new glossary\n",
        "generated vocabulary\n",
        glossary_path=glossary_path,
        vale_path=vale_path,
    )

    assert any(
        "out of date" in error
        and "glossary.mdx" in error
        for error in errors
    )


def test_check_outputs_detects_missing_file(
    tmp_path: Path,
) -> None:
    glossary_path = tmp_path / "glossary.mdx"
    vale_path = tmp_path / "accept.txt"

    glossary_path.write_text(
        "generated glossary\n",
        encoding="utf-8",
    )

    errors = generate_glossary.check_outputs(
        "generated glossary\n",
        "generated vocabulary\n",
        glossary_path=glossary_path,
        vale_path=vale_path,
    )

    assert any(
        "Missing generated file" in error
        and "accept.txt" in error
        for error in errors
    )

def test_loads_vale_only_terms(
    tmp_path: Path,
) -> None:
    source = tmp_path / "vale-accept.txt"
    source.write_text(
        """
# Vale-only terms

Pydantic
pytest
""",
        encoding="utf-8",
    )

    result = generate_glossary.load_vale_accept_terms(
        source
    )

    assert result == [
        "Pydantic",
        "pytest",
    ]