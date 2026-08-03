
from bs4 import BeautifulSoup, Comment, Tag


def normalize_html(html: str) -> str:
    """Remove non-content elements and normalize document HTML."""

    if not html.strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for element in soup.find_all(["script", "style", "noscript"]):
        element.decompose()

    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()

    for element in soup.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6"]
    ):
        if isinstance(element, Tag) and not element.get_text(strip=True):
            element.decompose()

    return str(soup).strip()