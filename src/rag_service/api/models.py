from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]

NonEmptyStringList = Annotated[
    list[NonEmptyString],
    Field(min_length=1),
]

FilterValue = NonEmptyString | NonEmptyStringList


class SearchFilters(BaseModel):
    """Supported metadata filters for hybrid search."""

    model_config = ConfigDict(extra="forbid")

    document_id: FilterValue | None = Field(
        default=None,
        description=(
            "Limit results to chunks from specific documents using the document IDs "
            "created by the RAG service, such as 'wordpress:page:123'. "
            "Copy the document_id from a search result to use it as a filter. "
            "Provide one ID as a string or multiple IDs as a list of strings, such "
            "as ['wordpress:page:123', 'wordpress:page:124'].\n\n"
            "If omitted, results are not restricted by document ID."
        ),
    )
    source: FilterValue | None = Field(
        default=None,
        description=(
            "Limit results to one or more content sources. "
            "If omitted, searches content from all sources in the index.\n\n"
            "Currently, only 'wordpress' is supported, so omitting this filter "
            "still searches only WordPress content."
        ),
    )
    source_id: FilterValue | None = Field(
        default=None,
        description=(
            "Limit results to chunks from specific documents using their original "
            "IDs in the source system. For WordPress, use the post or page ID "
            "as a string, such as '123'. Provide one ID as a string or multiple IDs "
            "as a list of strings, such as ['123', '124'].\n\n"
            "If omitted, results are not restricted by source-system document ID."
        ),
    )
    content_type: FilterValue | None = Field(
        default=None,
        description=(
            "Limit results by the type of document the content came from, "
            "such as 'post' or 'page' for WordPress content. Provide one type "
            "as a string or multiple types as a list of strings, such as ['post', 'page'].\n\n"
            "If omitted, searches all content types in the index."
        ),
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
    anchor: str | None = Field(
        default=None,
        description="Source anchor for the retrieved chunk's current heading.",
    )
    excerpt: str = Field(
        description="Text from the retrieved chunk.",
    )
    url: str = Field(
        description="Trusted URL for the source document.",
    )
    score: float = Field(
        description="Rerank score for the result.",
    )


class SearchResponse(BaseModel):
    """Successful response from POST /v1/search."""

    query: str = Field(
        description="The search query submitted by the client.",
    )

    results: list[SearchResult] = Field(
        description="Ranked search results that met the retrieval threshold.",
    )

class AnswerRequest(BaseModel):
    """Request body for POST /v1/answer."""

    model_config = ConfigDict(extra="forbid")

    query: NonEmptyString = Field(
        description="Natural-language question to answer.",
        examples=[
            "Why does inconsistent terminology cause retrieval failures?"
        ],
    )
    filters: SearchFilters | None = Field(
        default=None,
        description="Optional metadata filters applied during retrieval.",
    )


class AnswerSource(BaseModel):
    """One validated source supporting a generated answer."""

    citation_id: str = Field(
        description=(
            "Request-local citation identifier used in the generated answer."
        ),
        examples=["S1"],
    )
    chunk_id: str = Field(
        description="Stable identifier for the supporting chunk.",
    )
    document_id: str = Field(
        description="Stable identifier for the source document.",
    )
    title: str = Field(
        description="Title of the source document.",
    )
    heading_path: list[str] = Field(
        description="Heading hierarchy containing the supporting chunk.",
    )
    anchor: str | None = Field(
        default=None,
        description="Source anchor for the supporting chunk's current heading.",
    )
    excerpt: str = Field(
        description="Text from the supporting chunk.",
    )
    url: str = Field(
        description="Trusted URL for the source document.",
    )


class AnswerResponse(BaseModel):
    """Successful response from POST /v1/answer."""

    query: str = Field(
        description="The question submitted by the client.",
    )
    answer: str = Field(
        description="Grounded answer generated from retrieved evidence.",
    )
    sources: list[AnswerSource] = Field(
        description="Validated sources cited by the generated answer.",
    )
    sufficient_evidence: bool = Field(
        description=(
            "Whether the retrieved sources contained enough evidence "
            "to answer the question."
        ),
    )

class HealthResponse(BaseModel):
    """Successful response from GET /health."""

    status: str = Field(
        description="Current service health status.",
        examples=["ok"],
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


# Public API error information.
class ErrorBody(BaseModel):
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