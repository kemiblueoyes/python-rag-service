from rag_service.processing.html_parser import parse_html


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