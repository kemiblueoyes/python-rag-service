from rag_service.processing.normalize import normalize_html


def test_removes_scripts_and_styles() -> None:
    html = """
    <html>
        <style>.hidden { display:none; }</style>
        <script>alert("test");</script>
        <p>Visible content.</p>
    </html>
    """

    result = normalize_html(html)

    assert "script" not in result
    assert "style" not in result
    assert "Visible content." in result


def test_removes_html_comments() -> None:
    html = """
    <p>Before</p>
    <!-- This should not appear -->
    <p>After</p>
    """

    result = normalize_html(html)

    assert "This should not appear" not in result
    assert "Before" in result
    assert "After" in result


def test_removes_empty_content_elements() -> None:
    html = """
    <h2></h2>
    <p>   </p>
    <h2>Useful heading</h2>
    """

    result = normalize_html(html)

    assert "<h2></h2>" not in result
    assert "<p>   </p>" not in result
    assert "Useful heading" in result


def test_returns_empty_string_for_empty_input() -> None:
    assert normalize_html("") == ""