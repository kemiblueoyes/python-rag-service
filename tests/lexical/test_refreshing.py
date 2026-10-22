from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock

import pytest

from rag_service.config import Settings
from rag_service.lexical import refreshing


def test_active_search_finishes_before_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "corpus.json"
    path.write_text("old")
    entered, release = Event(), Event()
    old, new = MagicMock(), MagicMock()

    def search(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return []

    old.search.side_effect = search
    new.search.return_value = []
    builder = MagicMock(side_effect=[old, new])
    monkeypatch.setattr(refreshing, "create_lexical_retriever", builder)
    retriever = refreshing.RefreshingLexicalRetriever(
        Settings(lexical_corpus_path=path)
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(retriever.search, "query", 1)
        assert entered.wait(10)
        replacement = tmp_path / "replacement.json"
        replacement.write_text("new")
        replacement.replace(path)
        second = pool.submit(retriever.search, "query", 1)
        assert builder.call_count == 1
        old.close.assert_not_called()
        release.set()
        assert first.result(timeout=10) == []
        assert second.result(timeout=10) == []
    assert builder.call_count == 2
    old.close.assert_not_called()
    new.search.assert_called_once()


def test_replacement_during_build_is_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "corpus.json"
    path.write_text("old")
    obsolete, current = MagicMock(), MagicMock()
    current.search.return_value = []

    def build(settings):
        if builder.call_count == 1:
            replacement = tmp_path / "replacement.json"
            replacement.write_text("new")
            replacement.replace(path)
            return obsolete
        return current

    builder = MagicMock(side_effect=build)
    monkeypatch.setattr(refreshing, "create_lexical_retriever", builder)
    retriever = refreshing.RefreshingLexicalRetriever(
        Settings(lexical_corpus_path=path)
    )
    assert retriever.search("query", 1) == []
    assert builder.call_count == 2
    obsolete.search.assert_not_called()
    current.search.assert_called_once()
