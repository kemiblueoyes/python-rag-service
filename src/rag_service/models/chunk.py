from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A retrieval-ready chunk derived from a canonical document."""

    chunk_id: str
    document_id: str

    source: str
    source_id: str

    title: str
    url: str
    content_type: str

    text: str
    heading_path: list[str] = Field(default_factory=list)
    sequence: int
    block_types: list[str] = Field(default_factory=list)
    block_metadata: list[dict[str, Any]] = Field(default_factory=list)
    anchor: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    published_at: datetime | None = None
    modified_at: datetime | None = None
