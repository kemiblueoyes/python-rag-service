import pytest

from rag_service.generation.answer_generator import AnswerGenerator
from rag_service.generation.citation_validator import (
    CitationValidator,
)
from rag_service.generation.context_assembler import ContextAssembler
from rag_service.generation.errors import CitationValidationError
from rag_service.generation.models import (
    GenerationPrompt,
    ProposedAnswer,
)
from rag_service.generation.prompt_builder import PromptBuilder
from rag_service.models.chunk import DocumentChunk
from rag_service.retrieval.models import RetrievalResult


class CharacterTokenCounter:
    """Use character counts as deterministic test token counts."""

    def count_tokens(self, text: str) -> int:
        return len(text)


class StubLanguageModel:
    """Return a configured answer and retain the received prompt."""

    def __init__(self, answer: ProposedAnswer) -> None:
        self.answer = answer
        self.prompt: GenerationPrompt | None = None

    def generate(
        self,
        prompt: GenerationPrompt,
    ) -> ProposedAnswer:
        self.prompt = prompt
        return self.answer


def make_result(
    *,
    chunk_id: str,
    document_id: str,
    title: str,
    score: float,
) -> RetrievalResult:
    """Create one ranked retrieval result."""

    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source="wordpress",
        source_id=document_id,
        title=title,
        url=f"https://example.com/{document_id}",
        content_type="post",
        text=f"Evidence from {title}.",
        heading_path=["Retrieval"],
        sequence=0,
        metadata={},
        published_at=None,
        modified_at=None,
    )

    return RetrievalResult(
        chunk=chunk,
        score=score,
    )


def make_generator(
    answer: ProposedAnswer,
) -> tuple[AnswerGenerator, StubLanguageModel]:
    """Create an answer generator with real workflow components."""

    language_model = StubLanguageModel(answer)

    generator = AnswerGenerator(
        context_assembler=ContextAssembler(
            token_counter=CharacterTokenCounter(),
            max_context_tokens=10_000,
        ),
        prompt_builder=PromptBuilder(),
        language_model=language_model,
        citation_validator=CitationValidator(),
    )

    return generator, language_model


def test_answer_generator_returns_only_cited_sources() -> None:
    generator, language_model = make_generator(
        ProposedAnswer(
            answer="The second source contains the answer [S2].",
            citation_ids=["S2"],
            sufficient_evidence=True,
        )
    )
    first = make_result(
        chunk_id="chunk-1",
        document_id="document-1",
        title="First source",
        score=0.93,
    )
    second = make_result(
        chunk_id="chunk-2",
        document_id="document-2",
        title="Second source",
        score=0.88,
    )

    result = generator.generate(
        question="Which source contains the answer?",
        results=[first, second],
    )

    assert result.answer == (
        "The second source contains the answer [S2]."
    )
    assert result.sufficient_evidence is True
    assert len(result.sources) == 1
    assert result.sources[0].citation_id == "S2"
    assert result.sources[0].chunk is second.chunk

    assert language_model.prompt is not None
    assert "[SOURCE S1]" in language_model.prompt.user_message
    assert "[SOURCE S2]" in language_model.prompt.user_message


def test_answer_generator_returns_insufficient_answer_without_sources() -> None:
    generator, language_model = make_generator(
        ProposedAnswer(
            answer="The available sources are insufficient.",
            citation_ids=[],
            sufficient_evidence=False,
        )
    )

    result = generator.generate(
        question="What is the unsupported answer?",
        results=[],
    )

    assert result.answer == (
        "The available sources are insufficient."
    )
    assert result.sources == ()
    assert result.sufficient_evidence is False

    assert language_model.prompt is not None
    assert language_model.prompt.user_message.endswith(
        "Sources:\n"
    )


def test_answer_generator_propagates_invalid_citation() -> None:
    generator, _language_model = make_generator(
        ProposedAnswer(
            answer="The answer is supported [S2].",
            citation_ids=["S2"],
            sufficient_evidence=True,
        )
    )
    result = make_result(
        chunk_id="chunk-1",
        document_id="document-1",
        title="Only source",
        score=0.93,
    )

    with pytest.raises(
        CitationValidationError,
        match="sources that were not supplied",
    ):
        generator.generate(
            question="What is the answer?",
            results=[result],
        )