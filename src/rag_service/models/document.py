from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CanonicalDocument(BaseModel):
    # Stable identifier used inside the RAG service.
    document_id: str

    # Source platform, such as "wordpress" or "confluence".
    source: str

    # Identifier assigned by the original source platform.
    source_id: str

    # Title displayed to users.
    title: str

    # Trusted URL for the original document.
    url: str

    # Source content before cleaning and chunking.
    body: str

    # General source content type, such as "page", "post", or "article".
    content_type: str

    # Describes whether this is primary content or a listing page.
    document_role: Literal["content", "landing", "archive"] = "content"

    # Determines whether the document should enter the retrieval index.
    indexable: bool = True

    # Platform- or site-specific metadata preserved by the connector.
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Original publication date, when available.
    published_at: datetime | None = None

    # Most recent source modification date, when available.
    modified_at: datetime | None = None
