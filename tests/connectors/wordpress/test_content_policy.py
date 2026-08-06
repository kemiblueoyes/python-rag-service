from bs4 import BeautifulSoup, Tag

from rag_service.connectors.wordpress.content_policy import (
    build_wordpress_block_preserver,
)
from rag_service.processing.html_parser import parse_html

PRESERVED_CLASSES = frozenset({"wp-block-accordion"})


def test_recognizes_wordpress_accordion() -> None:
    soup = BeautifulSoup(
        '<div class="wp-block-accordion extra-class"></div>', "html.parser"
    )
    element = soup.div

    assert isinstance(element, Tag)
    preserve_block = build_wordpress_block_preserver(PRESERVED_CLASSES)
    assert preserve_block(element)


def test_does_not_match_unrelated_wordpress_block() -> None:
    soup = BeautifulSoup('<div class="wp-block-group"></div>', "html.parser")
    element = soup.div

    assert isinstance(element, Tag)
    preserve_block = build_wordpress_block_preserver(PRESERVED_CLASSES)
    assert not preserve_block(element)


def test_recognizes_any_configured_class() -> None:
    soup = BeautifulSoup('<div class="wp-block-tabs extra-class"></div>', "html.parser")
    element = soup.div

    assert isinstance(element, Tag)
    preserve_block = build_wordpress_block_preserver(
        {"wp-block-accordion", "wp-block-tabs"}
    )
    assert preserve_block(element)


def test_wordpress_policy_preserves_accordion_during_parsing() -> None:
    html = """
    <p>Before accordion.</p>
    <div class="wp-block-accordion">
        <h3>Accordion title</h3>
        <p>Accordion content.</p>
    </div>
    <p>After accordion.</p>
    """

    blocks = parse_html(
        html,
        preserve_block=build_wordpress_block_preserver(PRESERVED_CLASSES),
    )

    assert [block.block_type for block in blocks] == [
        "paragraph",
        "html_block",
        "paragraph",
    ]
    assert blocks[1].text.count("Accordion content.") == 1
