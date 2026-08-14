from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]

FilterValue = NonEmptyString | list[NonEmptyString]


class SearchFilters(BaseModel):
    """Supported metadata filters for semantic search."""

    model_config = ConfigDict(extra="forbid")

    document_id: FilterValue | None = Field(
        default=None,
        description="Limit results to one or more canonical document IDs.",
    )
    source: FilterValue | None = Field(
        default=None,
        description="Limit results to one or more content sources.",
    )
    source_id: FilterValue | None = Field(
        default=None,
        description="Limit results to one or more source-system document IDs.",
    )
    content_type: FilterValue | None = Field(
        default=None,
        description="Limit results to one or more content types.",
    )


class SearchRequest(BaseModel):
    """Request body for POST /v1/search."""

    model_config = ConfigDict(extra="forbid")

    query: NonEmptyString = Field(
        description="Natural-language search query.",
        examples=["How does metadata improve retrieval?"],
    )
    filters: SearchFilters | None = Field(
        default=None,
        description="Optional metadata filters applied during retrieval.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        description="Maximum number of search results to retrieve.",
        examples=[5],
    )


class SearchResult(BaseModel):
    """One ranked search result."""

    chunk_id: str = Field(
        description="Stable identifier for the retrieved chunk.",
    )
    document_id: str = Field(
        description="Stable identifier for the source document.",
    )
    title: str = Field(
        description="Title of the source document.",
    )
    heading_path: list[str] = Field(
        description="Heading hierarchy containing the retrieved chunk.",
    )
    excerpt: str = Field(
        description="Text from the retrieved chunk.",
    )
    url: str = Field(
        description="Trusted URL for the source document.",
    )
    score: float = Field(
        description="Semantic similarity score for the result.",
    )


class SearchResponse(BaseModel):
    """Successful response from POST /v1/search."""

    query: str = Field(
        description="The search query submitted by the client.",
    )
    results: list[SearchResult] = Field(
        description="Ranked search results that met the retrieval threshold.",
    )

class ErrorDetail(BaseModel):
    """Details about one request error."""

    field: str | None = Field(
        default=None,
        description="Request field associated with the error.",
        examples=["filters.site_id"],
    )
    message: str = Field(
        description="Human-readable description of the error.",
    )


class ErrorBody(BaseModel):
    """Public API error information."""

    code: str = Field(
        description="Stable machine-readable error code.",
        examples=["validation_error"],
    )
    message: str = Field(
        description="Human-readable summary of the error.",
    )
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="Additional error details.",
    )


class ErrorResponse(BaseModel):
    """Standard error response returned by the public API."""

    error: ErrorBody