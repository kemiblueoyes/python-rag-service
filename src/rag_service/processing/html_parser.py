
from bs4 import BeautifulSoup, Tag

from rag_service.processing.models import ContentBlock

from rag_service.processing.normalize import normalize_html


def parse_html(html: str) -> list[ContentBlock]:
    """Convert document HTML into ordered content blocks."""

    normalized_html = normalize_html(html)
    soup = BeautifulSoup(normalized_html, "html.parser")
    blocks: list[ContentBlock] = []

    for element in soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "pre", "blockquote"]
    ):
        if not isinstance(element, Tag):
            continue

        text = element.get_text(" ", strip=True)

        if not text:
            continue

        if element.name.startswith("h"):
            blocks.append(
                ContentBlock(
                    block_type="heading",
                    text=text,
                    heading_level=int(element.name[1]),
                    anchor=element.get("id"),
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
            blocks.append(
                ContentBlock(
                    block_type="code",
                    text=text,
                )
            )
        elif element.name == "blockquote":
            blocks.append(
                ContentBlock(
                    block_type="quote",
                    text=text,
                )
            )
        else:
            blocks.append(
                ContentBlock(
                    block_type="paragraph",
                    text=text,
                )
            )

    return blocks