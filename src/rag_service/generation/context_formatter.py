from collections.abc import Sequence

from rag_service.generation.models import ContextSource


def format_context_source(source: ContextSource) -> str:
    """Format one context source for inclusion in a model prompt."""

    lines = [
        f"[SOURCE {source.citation_id}]",
        f"Title: {source.chunk.title}",
    ]

    if source.chunk.heading_path:
        lines.append(
            f"Heading: {' > '.join(source.chunk.heading_path)}"
        )

    lines.extend(
        [
            "Content:",
            source.chunk.text,
            f"[END SOURCE {source.citation_id}]",
        ]
    )

    return "\n".join(lines)


def format_context_sources(
    sources: Sequence[ContextSource],
) -> str:
    """Format ordered context sources for inclusion in a model prompt."""

    return "\n\n".join(
        format_context_source(source)
        for source in sources
    )