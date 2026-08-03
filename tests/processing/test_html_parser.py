from bs4 import Tag

from rag_service.processing.html_parser import parse_html


def preserve_interactive_panel(element: Tag) -> bool:
    classes = {str(value) for value in element.get_attribute_list("class")}
    return "interactive-panel" in classes


def test_parse_html_preserves_block_order() -> None:
    html = """
    <h2 id="retrieval-failures">Retrieval failures</h2>
    <p>Retrieval can fail for several reasons.</p>
    <ul>
        <li>Vocabulary mismatch</li>
        <li>Missing context</li>
    </ul>
    <blockquote>Good retrieval depends on good content.</blockquote>
    <pre><code>result = search(query)</code></pre>
    """

    blocks = parse_html(html)

    assert [block.block_type for block in blocks] == [
        "heading",
        "paragraph",
        "list",
        "quote",
        "code",
    ]


def test_parse_html_extracts_heading_metadata() -> None:
    html = '<h3 id="vocabulary-mismatch">Vocabulary mismatch</h3>'

    blocks = parse_html(html)

    assert len(blocks) == 1
    assert blocks[0].block_type == "heading"
    assert blocks[0].text == "Vocabulary mismatch"
    assert blocks[0].heading_level == 3
    assert blocks[0].anchor == "vocabulary-mismatch"


def test_parse_html_formats_list_items() -> None:
    html = """
    <ol>
        <li>Retrieve content</li>
        <li>Generate embeddings</li>
    </ol>
    """

    blocks = parse_html(html)

    assert len(blocks) == 1
    assert blocks[0].block_type == "list"
    assert blocks[0].text == "- Retrieve content\n- Generate embeddings"


def test_parse_html_normalizes_nested_inline_text() -> None:
    html = """
    <p>
        Metadata <strong>improves</strong>
        <a href="/retrieval">retrieval quality</a>.
    </p>
    """

    blocks = parse_html(html)

    assert len(blocks) == 1
    assert blocks[0].text == "Metadata improves retrieval quality ."


def test_parse_html_ignores_empty_elements() -> None:
    html = """
    <h2></h2>
    <p>   </p>
    <p>Useful content.</p>
    """

    blocks = parse_html(html)

    assert len(blocks) == 1
    assert blocks[0].block_type == "paragraph"
    assert blocks[0].text == "Useful content."


def test_parse_html_returns_empty_list_for_empty_html() -> None:
    assert parse_html("") == []


def test_parse_html_preserves_table_content() -> None:
    html = """
    <table>
        <tr>
            <th>Feature</th>
            <th>Description</th>
        </tr>
        <tr>
            <td>Chunking</td>
            <td>Splits documents into retrieval units.</td>
        </tr>
    </table>
    """

    blocks = parse_html(html)

    assert len(blocks) == 1
    assert blocks[0].block_type == "table"
    assert "Chunking" in blocks[0].text
    assert "Splits documents into retrieval units." in blocks[0].text
    assert "html" in blocks[0].metadata
    assert "<table>" in blocks[0].metadata["html"]


def test_parse_html_preserves_a_component_selected_by_policy() -> None:
    html = """
    <div class="interactive-panel">
        <h3>Knowledge Systems in Software Companies</h3>
        <div class="interactive-panel-body">
            <div class="infographic-body">
                <p>Product knowledge flows through documentation systems.</p>
            </div>
        </div>
    </div>
    """

    blocks = parse_html(html, preserve_block=preserve_interactive_panel)

    assert len(blocks) == 1
    assert blocks[0].block_type == "html_block"
    assert "Knowledge Systems in Software Companies" in blocks[0].text
    assert "Product knowledge flows through documentation systems." in blocks[0].text
    assert "html" in blocks[0].metadata
    assert "interactive-panel" in blocks[0].metadata["class"]


def test_parse_html_does_not_duplicate_preserved_component_children() -> None:
    html = """
    <p>Before component.</p>

    <div class="interactive-panel">
        <h3>Diagram title</h3>
        <div class="interactive-panel-body">
            <div class="diagram-body">
                <p>Diagram content.</p>
            </div>
        </div>
    </div>

    <p>After component.</p>
    """

    blocks = parse_html(html, preserve_block=preserve_interactive_panel)

    assert [block.block_type for block in blocks] == [
        "paragraph",
        "html_block",
        "paragraph",
    ]

    assert blocks[1].text.count("Diagram content.") == 1


def test_parse_html_does_not_assume_unknown_components_are_preserved() -> None:
    html = """
    <div class="source-specific-component">
        <h3>Component heading</h3>
        <p>Component content.</p>
    </div>
    """

    blocks = parse_html(html)

    assert [block.block_type for block in blocks] == ["heading", "paragraph"]
