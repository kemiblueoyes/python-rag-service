import json
from pathlib import Path

from pydantic import ValidationError

from rag_service.config import Settings
from rag_service.errors import ServiceConfigurationError
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

    try:
        chunks = load_lexical_corpus(settings.lexical_corpus_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, ValueError):
        raise _invalid_lexical_corpus() from None

    try:
        return Bm25Retriever(chunks)
    except ValueError:
        raise _invalid_lexical_corpus() from None


def _invalid_lexical_corpus() -> ServiceConfigurationError:
    return ServiceConfigurationError(
        operation="retrieval",
        reason="invalid_lexical_corpus",
        diagnostic=(
            "Check LEXICAL_CORPUS_PATH. Use a readable JSON list of valid chunks."
        ),
    )