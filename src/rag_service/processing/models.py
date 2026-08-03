
from typing import Literal

from pydantic import BaseModel


class ContentBlock(BaseModel):
    """A meaningful block extracted from a document's HTML."""

    block_type: Literal["heading", "paragraph", "list", "code", "quote"]
    text: str
    heading_level: int | None = None
    anchor: str | None = None