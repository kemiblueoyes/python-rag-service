from collections.abc import Callable

from bs4 import BeautifulSoup, Tag

from rag_service.processing.models import ContentBlock
from rag_service.processing.normalize import normalize_html

PreservedBlockPredicate = Callable[[Tag], bool]


def _never_preserve_block(_element: Tag) -> bool:
    return False


def parse_html(
    html: str,
    *,
    preserve_block: PreservedBlockPredicate | None = None,
) -> list[ContentBlock]:
    """Convert document HTML into ordered, source-neutral content blocks.

    Connectors can supply ``preserve_block`` to identify source-specific HTML
    components that must be represented as one atomic ``html_block``.
    """

    normalized_html = normalize_html(html)
    soup = BeautifulSoup(normalized_html, "html.parser")
    blocks: list[ContentBlock] = []
    should_preserve = preserve_block or _never_preserve_block

    for element in soup.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "ul",
            "ol",
            "pre",
            "blockquote",
            "table",
            "div",
        ]
    ):
        if not isinstance(element, Tag):
            continue

        preserved = should_preserve(element)

        # Do not separately parse content inside a preserved component.
        if not preserved and any(
            isinstance(parent, Tag) and should_preserve(parent)
            for parent in element.parents
        ):
            continue

        text = element.get_text(" ", strip=True)

        if not text:
            continue

        if preserved:
            blocks.append(
                ContentBlock(
                    block_type="html_block",
                    text=text,
                    metadata={
                        "html": str(element),
                        "class": [
                            str(value) for value in element.get_attribute_list("class")
                        ],
                    },
                )
            )
            continue

        if element.name.startswith("h"):
            id_attribute = element.get("id")
            anchor = id_attribute if isinstance(id_attribute, str) else None

            blocks.append(
                ContentBlock(
                    block_type="heading",
                    text=text,
                    heading_level=int(element.name[1]),
                    anchor=anchor,
                )
            )

        elif element.name in {"ul", "ol"}:
            items = [
                item.get_text(" ", strip=True)
                for item in element.find_all("li", recursive=False)
            ]

            blocks.append(
                ContentBlock(
                    block_type="list",
                    text="\n".join(f"- {item}" for item in items if item),
                )
            )

        elif element.name == "pre":
            blocks.append(ContentBlock(block_type="code", text=text))

        elif element.name == "blockquote":
            blocks.append(ContentBlock(block_type="quote", text=text))

        elif element.name == "table":
            blocks.append(
                ContentBlock(
                    block_type="table",
                    text=text,
                    metadata={"html": str(element)},
                )
            )

        elif element.name == "p":
            blocks.append(ContentBlock(block_type="paragraph", text=text))

    return blocks
