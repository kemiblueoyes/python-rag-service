from rag_service.embeddings.base import EmbeddingProvider
from rag_service.lexical.base import LexicalRetriever
from rag_service.reranking.base import Reranker
from rag_service.retrieval.errors import RetrievalUnavailableError
from rag_service.retrieval.fusion import reciprocal_rank_fusion
from rag_service.retrieval.models import (
    RetrievalRequest,
    RetrievalResult,
)
from rag_service.vectorstores.base import SearchResult, VectorStore


class RetrievalService:
    """Shared hybrid retrieval pipeline used by search and answer generation."""

    _SUPPORTED_FILTERS = frozenset(
        {
            "document_id",
            "source",
            "source_id",
            "content_type",
        }
    )

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        lexical_retriever: LexicalRetriever,
        reranker: Reranker,
        vector_candidate_depth: int = 20,
        lexical_candidate_depth: int = 20,
        fused_candidate_depth: int = 20,
        rrf_k: int = 60,
        support_cutoff: float = 0.70,
    ) -> None:
        if vector_candidate_depth < 1:
            raise ValueError(
                "Vector candidate depth must be at least 1."
            )

        if lexical_candidate_depth < 1:
            raise ValueError(
                "Lexical candidate depth must be at least 1."
            )

        if fused_candidate_depth < 1:
            raise ValueError(
                "Fused candidate depth must be at least 1."
            )

        if rrf_k < 1:
            raise ValueError(
                "RRF constant must be at least 1."
            )

        if not 0.0 <= support_cutoff <= 1.0:
            raise ValueError(
                "Support cutoff must be between 0 and 1."
            )

        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._lexical_retriever = lexical_retriever
        self._reranker = reranker
        self._vector_candidate_depth = vector_candidate_depth
        self._lexical_candidate_depth = lexical_candidate_depth
        self._fused_candidate_depth = fused_candidate_depth
        self._rrf_k = rrf_k
        self._support_cutoff = support_cutoff

    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> list[RetrievalResult]:
        self._validate_request(request)

        query = request.query.strip()
        filters = request.filters or None

        try:
            query_vector = self._embedding_provider.embed_query(
                query
            )

            vector_results = self._vector_store.search(
                query_vector=query_vector,
                limit=self._vector_candidate_depth,
                filters=filters,
            )

            lexical_results = self._lexical_retriever.search(
                query,
                limit=self._lexical_candidate_depth,
                filters=filters,
            )

            vector_results = self._deduplicate_results(
                vector_results
            )
            lexical_results = self._deduplicate_results(
                lexical_results
            )

            fused_results = reciprocal_rank_fusion(
                [
                    vector_results,
                    lexical_results,
                ],
                k=self._rrf_k,
            )

            candidates = [
                fused.result
                for fused in fused_results[
                    : self._fused_candidate_depth
                ]
            ]

            if not candidates:
                return []

            reranked_results = self._reranker.rerank(
                query,
                candidates,
                limit=min(
                    request.limit,
                    len(candidates),
                ),
            )

        except Exception as exc:
            raise RetrievalUnavailableError(
                "Retrieval could not be completed."
            ) from exc

        if not reranked_results:
            return []

        if (
            reranked_results[0].score
            < self._support_cutoff
        ):
            return []

        return [
            RetrievalResult(
                chunk=result.chunk,
                score=result.score,
            )
            for result in reranked_results[
                : request.limit
            ]
        ]

    @classmethod
    def _validate_request(
        cls,
        request: RetrievalRequest,
    ) -> None:
        if not request.query.strip():
            raise ValueError(
                "Query must not be empty."
            )

        if request.limit < 1:
            raise ValueError(
                "Retrieval limit must be at least 1."
            )

        cls._validate_filters(
            request.filters
        )

    @classmethod
    def _validate_filters(
        cls,
        filters: dict[str, object],
    ) -> None:
        unsupported = sorted(
            set(filters) - cls._SUPPORTED_FILTERS
        )

        if unsupported:
            names = ", ".join(unsupported)
            raise ValueError(
                f"Unsupported retrieval filter(s): {names}"
            )

        for key, value in filters.items():
            if isinstance(value, str):
                if not value.strip():
                    raise ValueError(
                        f"Filter {key!r} must not be empty."
                    )
                continue

            if isinstance(
                value,
                (
                    list,
                    tuple,
                    set,
                    frozenset,
                ),
            ):
                if not value:
                    raise ValueError(
                        f"Filter {key!r} must not be empty."
                    )

                if not all(
                    isinstance(item, str)
                    and item.strip()
                    for item in value
                ):
                    raise ValueError(
                        f"Filter {key!r} must contain "
                        "only non-empty strings."
                    )
                continue

            raise ValueError(
                f"Filter {key!r} must be a string "
                "or collection of strings."
            )

    @staticmethod
    def _deduplicate_results(
        results: list[SearchResult],
    ) -> list[SearchResult]:
        seen_chunk_ids: set[str] = set()
        unique_results: list[SearchResult] = []

        for result in results:
            if (
                result.chunk.chunk_id
                in seen_chunk_ids
            ):
                continue

            seen_chunk_ids.add(
                result.chunk.chunk_id
            )
            unique_results.append(
                result
            )

        return unique_results