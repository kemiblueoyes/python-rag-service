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
    assert "content_type: glossary" in result
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
        terms
    )

    assert result == (
        "Hybrid retrieval\n"
        "Hybrid search\n"
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