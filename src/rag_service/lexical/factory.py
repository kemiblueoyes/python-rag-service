import json
from pathlib import Path

from rag_service.config import Settings
from rag_service.lexical.base import LexicalRetriever
from rag_service.lexical.bm25 import Bm25Retriever
from rag_service.models.chunk import DocumentChunk


def load_lexical_corpus(
    path: Path,
) -> list[DocumentChunk]:
    """Load retrieval-ready chunks used to build the BM25 index."""

    if not path.exists():
        raise FileNotFoundError(
            f"Lexical corpus does not exist: {path}"
        )

    payload: object = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(payload, list):
        raise ValueError(
            f"Expected a chunk list in {path}"
        )

    return [
        DocumentChunk.model_validate(item)
        for item in payload
    ]


def create_lexical_retriever(
    settings: Settings,
) -> LexicalRetriever:
    """Build the configured lexical retriever."""

    chunks = load_lexical_corpus(
        settings.lexical_corpus_path
    )

    return Bm25Retriever(chunks)