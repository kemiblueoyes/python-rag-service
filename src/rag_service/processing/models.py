from typing import Any, Literal

from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    """A structured piece of document content extracted from HTML."""

    block_type: Literal[
        "heading",
        "paragraph",
        "list",
        "code",
        "quote",
        "table",
        "html_block",
    ]

    text: str

    heading_level: int | None = None
    anchor: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)


class HeadingSection(BaseModel):
    """Content grouped beneath a single, fully qualified heading path."""

    heading_path: list[str] = Field(default_factory=list)
    blocks: list[ContentBlock] = Field(default_factory=list)
    anchor: str | None = None


class ChunkContent(BaseModel):
    """A heading-aware chunk before document metadata and IDs are attached."""

    text: str
    heading_path: list[str] = Field(default_factory=list)
    blocks: list[ContentBlock] = Field(default_factory=list)
    anchor: str | None = None
