from bs4 import BeautifulSoup, Tag
from pytest import MonkeyPatch

from rag_service.connectors.wordpress import content_policy
from rag_service.connectors.wordpress.content_policy import (
    is_preserved_wordpress_block,
)
from rag_service.processing.html_parser import parse_html


def test_recognizes_wordpress_accordion() -> None:
    soup = BeautifulSoup(
        '<div class="wp-block-accordion extra-class"></div>', "html.parser"
    )
    element = soup.div

    assert isinstance(element, Tag)
    assert is_preserved_wordpress_block(element)


def test_does_not_match_unrelated_wordpress_block() -> None:
    soup = BeautifulSoup('<div class="wp-block-group"></div>', "html.parser")
    element = soup.div

    assert isinstance(element, Tag)
    assert not is_preserved_wordpress_block(element)


def test_recognizes_any_class_added_to_the_policy(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        content_policy,
        "WORDPRESS_PRESERVED_BLOCK_CLASSES",
        frozenset({"wp-block-accordion", "wp-block-tabs"}),
    )
    soup = BeautifulSoup('<div class="wp-block-tabs extra-class"></div>', "html.parser")
    element = soup.div

    assert isinstance(element, Tag)
    assert content_policy.is_preserved_wordpress_block(element)


def test_wordpress_policy_preserves_accordion_during_parsing() -> None:
    html = """
    <p>Before accordion.</p>
    <div class="wp-block-accordion">
        <h3>Accordion title</h3>
        <p>Accordion content.</p>
    </div>
    <p>After accordion.</p>
    """

    blocks = parse_html(html, preserve_block=is_preserved_wordpress_block)

    assert [block.block_type for block in blocks] == [
        "paragraph",
        "html_block",
        "paragraph",
    ]
    assert blocks[1].text.count("Accordion content.") == 1
