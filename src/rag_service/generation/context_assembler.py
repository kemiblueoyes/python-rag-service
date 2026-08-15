from collections.abc import Sequence

from rag_service.generation.context_formatter import (
    format_context_sources,
)
from rag_service.generation.errors import ContextBudgetError
from rag_service.generation.models import (
    AssembledContext,
    ContextSource,
)
from rag_service.generation.token_counter import TokenCounter
from rag_service.retrieval.models import RetrievalResult


class ContextAssembler:
    """Select retrieved chunks that fit within a context token budget."""

    def __init__(
        self,
        *,
        token_counter: TokenCounter,
        max_context_tokens: int,
    ) -> None:
        if max_context_tokens <= 0:
            raise ValueError(
                "max_context_tokens must be greater than zero"
            )

        self._token_counter = token_counter
        self._max_context_tokens = max_context_tokens

    def assemble(
        self,
        results: Sequence[RetrievalResult],
    ) -> AssembledContext:
        """Assemble ranked retrieval results into model context."""

        selected_sources: list[ContextSource] = []
        token_count = 0

        for result in results:
            candidate_source = ContextSource(
                citation_id=f"S{len(selected_sources) + 1}",
                chunk=result.chunk,
                score=result.score,
            )
            candidate_sources = (
                *selected_sources,
                candidate_source,
            )
            formatted_context = format_context_sources(
                candidate_sources
            )
            candidate_token_count = (
                self._token_counter.count_tokens(
                    formatted_context
                )
            )

            if candidate_token_count > self._max_context_tokens:
                if not selected_sources:
                    raise ContextBudgetError(
                        budget_tokens=self._max_context_tokens,
                        required_tokens=candidate_token_count,
                    )

                break

            selected_sources.append(candidate_source)
            token_count = candidate_token_count

        return AssembledContext(
            sources=tuple(selected_sources),
            token_count=token_count,
        )