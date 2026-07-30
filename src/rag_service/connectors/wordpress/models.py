from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class WordPressRenderedField(BaseModel):
    """A WordPress field returned in rendered form."""

    rendered: str = ""


class WordPressPost(BaseModel):
    """A post-like record returned by the WordPress REST API."""

    # Unique WordPress database identifier.
    id: int

    # Publication date in UTC.
    date_gmt: datetime | None = None

    # Most recent modification date in UTC.
    modified_gmt: datetime | None = None

    # URL-safe identifier assigned by WordPress.
    slug: str

    # Publication status returned by WordPress.
    status: Literal[
        "publish",
        "future",
        "draft",
        "pending",
        "private",
        "trash",
    ]

    # WordPress post type, such as "post", "page", or a custom post type.
    type: str

    # Public URL for the content.
    link: str

    # Title object returned by the REST API.
    title: WordPressRenderedField

    # Rendered HTML body returned by the REST API.
    content: WordPressRenderedField

    # Rendered excerpt returned by the REST API.
    excerpt: WordPressRenderedField = Field(
        default_factory=WordPressRenderedField
    )

    # WordPress user ID for the author.
    author: int | None = None

    # Featured media attachment ID.
    featured_media: int | None = None

    # Category term IDs assigned to standard posts.
    categories: list[int] = Field(default_factory=list)

    # Tag term IDs assigned to standard posts.
    tags: list[int] = Field(default_factory=list)

    # Parent page or post ID, where supported.
    parent: int | None = None

    # Page ordering value, where supported.
    menu_order: int | None = None

    # Registered REST API metadata fields.
    meta: dict[str, Any] = Field(default_factory=dict)

    # Custom fields exposed through the WordPress REST API.
    acf: dict[str, Any] = Field(default_factory=dict)

    # Yoast document metadata from the WordPress REST API.
    yoast_head_json: dict[str, Any] | None = None