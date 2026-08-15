import pytest

from rag_service.generation.context_assembler import ContextAssembler
from rag_service.generation.context_formatter import (
    format_context_sources,
)
from rag_service.generation.errors import ContextBudgetError
from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval.models import RetrievalResult


class CharacterTokenCounter:
    """Use character counts as predictable test token counts."""

    def count_tokens(self, text: str) -> int:
        return len(text)


def make_result(
    *,
    chunk_id: str,
    text: str,
    score: float,
    heading_path: list[str] | None = None,
) -> RetrievalResult:
    """Create a retrieval result for context assembler tests."""

    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id=f"document-{chunk_id}",
        source="wordpress",
        source_id=f"source-{chunk_id}",
        title=f"Document {chunk_id}",
        url=f"https://example.com/{chunk_id}",
        content_type="post",
        text=text,
        heading_path=(
            ["Retrieval"]
            if heading_path is None
            else heading_path
        ),
        sequence=0,
        metadata={},
        published_at=None,
        modified_at=None,
    )

    return RetrievalResult(
        chunk=chunk,
        score=score,
    )


@pytest.mark.parametrize(
    "max_context_tokens",
    [0, -1],
)
def test_context_assembler_rejects_invalid_budget(
    max_context_tokens: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_context_tokens must be greater than zero",
    ):
        ContextAssembler(
            token_counter=CharacterTokenCounter(),
            max_context_tokens=max_context_tokens,
        )


def test_assemble_returns_empty_context_for_no_results() -> None:
    assembler = ContextAssembler(
        token_counter=CharacterTokenCounter(),
        max_context_tokens=1_000,
    )

    context = assembler.assemble([])

    assert context.sources == ()
    assert context.token_count == 0


def test_assemble_preserves_retrieval_order_and_assigns_citation_ids() -> None:
    results = [
        make_result(
            chunk_id="first",
            text="First result.",
            score=0.95,
        ),
        make_result(
            chunk_id="second",
            text="Second result.",
            score=0.88,
        ),
        make_result(
            chunk_id="third",
            text="Third result.",
            score=0.81,
        ),
    ]
    assembler = ContextAssembler(
        token_counter=CharacterTokenCounter(),
        max_context_tokens=10_000,
    )

    context = assembler.assemble(results)

    assert [
        source.citation_id
        for source in context.sources
    ] == ["S1", "S2", "S3"]
    assert [
        source.chunk.chunk_id
        for source in context.sources
    ] == ["first", "second", "third"]
    assert [
        source.score
        for source in context.sources
    ] == [0.95, 0.88, 0.81]


def test_assemble_reports_tokens_for_complete_formatted_context() -> None:
    results = [
        make_result(
            chunk_id="first",
            text="First result.",
            score=0.95,
        ),
        make_result(
            chunk_id="second",
            text="Second result.",
            score=0.88,
        ),
    ]
    assembler = ContextAssembler(
        token_counter=CharacterTokenCounter(),
        max_context_tokens=10_000,
    )

    context = assembler.assemble(results)

    formatted_context = format_context_sources(
        context.sources
    )

    assert context.token_count == len(formatted_context)


def test_assemble_stops_when_next_complete_source_does_not_fit() -> None:
    first_result = make_result(
        chunk_id="first",
        text="Short first result.",
        score=0.95,
    )
    second_result = make_result(
        chunk_id="second",
        text="A much longer second result. " * 20,
        score=0.88,
    )
    third_result = make_result(
        chunk_id="third",
        text="Short third result.",
        score=0.81,
    )

    sizing_assembler = ContextAssembler(
        token_counter=CharacterTokenCounter(),
        max_context_tokens=10_000,
    )
    first_context = sizing_assembler.assemble(
        [first_result]
    )

    assembler = ContextAssembler(
        token_counter=CharacterTokenCounter(),
        max_context_tokens=first_context.token_count + 10,
    )

    context = assembler.assemble(
        [
            first_result,
            second_result,
            third_result,
        ]
    )

    assert len(context.sources) == 1
    assert context.sources[0].chunk.chunk_id == "first"
    assert context.sources[0].chunk.text == (
        "Short first result."
    )


def test_assemble_raises_when_highest_ranked_source_cannot_fit() -> None:
    result = make_result(
        chunk_id="first",
        text="This source is too large for the configured budget.",
        score=0.95,
    )
    sizing_assembler = ContextAssembler(
        token_counter=CharacterTokenCounter(),
        max_context_tokens=10_000,
    )
    required_tokens = sizing_assembler.assemble(
        [result]
    ).token_count
    available_tokens = required_tokens - 1

    assembler = ContextAssembler(
        token_counter=CharacterTokenCounter(),
        max_context_tokens=available_tokens,
    )

    with pytest.raises(ContextBudgetError) as exc_info:
        assembler.assemble([result])

    assert exc_info.value.budget_tokens == available_tokens
    assert exc_info.value.required_tokens == required_tokens
    assert str(exc_info.value) == (
        "highest-ranked source exceeds the context token budget: "
        f"required {required_tokens}, "
        f"available {available_tokens}"
    )


def test_assemble_preserves_empty_heading_path() -> None:
    result = make_result(
        chunk_id="first",
        text="Content without a heading.",
        score=0.95,
        heading_path=[],
    )
    assembler = ContextAssembler(
        token_counter=CharacterTokenCounter(),
        max_context_tokens=10_000,
    )

    context = assembler.assemble([result])

    assert context.sources[0].chunk.heading_path == []