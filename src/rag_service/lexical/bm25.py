from collections.abc import Sequence
from typing import Any

import bm25s  # type: ignore[import-untyped]

from rag_service.models.chunk import DocumentChunk
from rag_service.vectorstores.base import SearchResult


class Bm25Retriever:
    """Find chunks by keyword match, ranked with BM25.
       The index is built in memory from the chunks passed at construction.
    """

    def __init__(
        self,
        chunks: Sequence[DocumentChunk],
    ) -> None:
        if not chunks:
            raise ValueError(
                "At least one chunk is required to build the BM25 index."
            )

        self._chunks = list(chunks)

        corpus = [
            self._document_for_index(chunk)
            for chunk in self._chunks
        ]

        corpus_tokens = bm25s.tokenize(
            corpus,
            stopwords="en",
        )

        self._retriever = bm25s.BM25()
        self._retriever.index(corpus_tokens)

    def search(
        self,
        query: str,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("Query must not be empty.")

        if limit < 1:
            raise ValueError("Search limit must be at least 1.")

        query_tokens = bm25s.tokenize(
            [query.strip()],
            stopwords="en",
        )

        document_ids, scores = self._retriever.retrieve(
            query_tokens,
            k=len(self._chunks),
        )

        results: list[SearchResult] = []

        for position in range(document_ids.shape[1]):
            chunk_index = int(document_ids[0, position])
            chunk = self._chunks[chunk_index]

            if filters and not self._matches_filters(
                chunk,
                filters,
            ):
                continue

            results.append(
                SearchResult(
                    chunk=chunk,
                    score=float(scores[0, position]),
                )
            )

            if len(results) >= limit:
                break

        return results

    @staticmethod
    def _document_for_index(
        chunk: DocumentChunk,
    ) -> str:
        heading = " > ".join(chunk.heading_path)

        parts = [
            chunk.title,
            heading,
            chunk.text,
        ]

        return "\n".join(
            part
            for part in parts
            if part
        )

    @staticmethod
    def _matches_filters(
        chunk: DocumentChunk,
        filters: dict[str, Any],
    ) -> bool:
        for key, expected in filters.items():
            if not hasattr(chunk, key):
                raise ValueError(
                    f"Unsupported lexical retrieval filter: {key}"
                )

            actual = getattr(chunk, key)

            if isinstance(expected, str):
                if actual != expected:
                    return False
                continue

            if isinstance(
                expected,
                (list, tuple, set, frozenset),
            ):
                if actual not in expected:
                    return False
                continue

            raise ValueError(
                f"Filter {key!r} must be a string "
                "or collection of strings."
            )

        return True