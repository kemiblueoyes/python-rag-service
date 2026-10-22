"""Refresh the process-local BM25 snapshot after corpus publication."""

from pathlib import Path
from threading import Lock
from typing import Any

from rag_service.config import Settings
from rag_service.lexical.base import LexicalRetriever
from rag_service.lexical.factory import (
    _invalid_lexical_corpus,
    create_lexical_retriever,
)
from rag_service.vectorstores.base import SearchResult


def _version(path: Path) -> tuple[int, int, int, int, int]:
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


class RefreshingLexicalRetriever:
    """Serialize snapshot construction and use without replacing provider clients.

    BM25 snapshots own only memory and have no closeable resources. Keeping the
    lock through search also avoids relying on the BM25 library's thread safety.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = Lock()
        self._version: tuple[int, int, int, int, int] | None = None
        self._retriever: LexicalRetriever | None = None
        with self._lock:
            self._refresh()

    def _refresh(self) -> None:
        try:
            for _ in range(3):
                version = _version(self._settings.lexical_corpus_path)
                if version == self._version:
                    return
                replacement = create_lexical_retriever(self._settings)
                if version == _version(self._settings.lexical_corpus_path):
                    self._retriever = replacement
                    self._version = version
                    return
        except OSError:
            raise _invalid_lexical_corpus() from None
        # A continuously changing file cannot provide a stable snapshot.
        raise _invalid_lexical_corpus()

    def search(
        self,
        query: str,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        with self._lock:
            self._refresh()
            assert self._retriever is not None
            return self._retriever.search(query, limit=limit, filters=filters)
