import json
from collections.abc import Sequence

from rag_service.generation.models import ContextSource

SourceRecord = dict[str, str | list[str]]


def source_record(source: ContextSource) -> SourceRecord:
    """Return the source fields that are sent to the language model."""

    return {
        "citation_id": source.citation_id,
        "title": source.chunk.title,
        "heading_path": list(source.chunk.heading_path),
        "content": source.chunk.text,
    }


def serialize_json(value: object) -> str:
    """Serialize a prompt value with the shared JSON settings."""

    return json.dumps(value, ensure_ascii=False)


def serialize_context_sources(
    sources: Sequence[ContextSource],
) -> str:
    """Serialize ordered sources exactly as they appear in the user message."""

    return serialize_json(
        [source_record(source) for source in sources]
    )


def serialize_user_message(
    *,
    question: str,
    sources: Sequence[ContextSource],
) -> str:
    """Serialize the question and sources as one JSON user message."""

    return serialize_json(
        {
            "question": question,
            "sources": [
                source_record(source) for source in sources
            ],
        }
    )
