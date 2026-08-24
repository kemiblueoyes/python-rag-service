from rag_service.models.canonical_document import CanonicalDocument
from rag_service.models.chunk import DocumentChunk
from rag_service.processing.chunk_metadata import build_document_chunks
from rag_service.processing.chunker import DEFAULT_MAX_CHARS, chunk_sections
from rag_service.processing.heading_hierarchy import build_heading_sections
from rag_service.processing.html_parser import PreservedBlockPredicate, parse_html
from rag_service.processing.identifiers import ChunkIdFactory
from rag_service.processing.models import HeadingSection


def _exclude_sections(
    sections: list[HeadingSection],
    excluded_headings: frozenset[str],
) -> list[HeadingSection]:
    """Remove sections whose heading path contains an excluded heading."""

    if not excluded_headings:
        return sections

    normalized_exclusions = {
        heading.strip().casefold()
        for heading in excluded_headings
    }

    return [
        section
        for section in sections
        if not any(
            heading.strip().casefold() in normalized_exclusions
            for heading in section.heading_path
        )
    ]

def process_document(
    document: CanonicalDocument,
    *,
    preserve_block: PreservedBlockPredicate | None = None,
    excluded_section_headings: frozenset[str] = frozenset(),
    max_chars: int = DEFAULT_MAX_CHARS,
    chunk_id_factory: ChunkIdFactory | None = None,
) -> list[DocumentChunk]:
    """Transform one canonical content document into retrieval-ready chunks."""

    if not document.indexable or document.document_role != "content":
        return []

    blocks = parse_html(document.body, preserve_block=preserve_block)
    sections = build_heading_sections(blocks)
    sections = _exclude_sections(
        sections,
        excluded_section_headings,
    )
    chunk_content = chunk_sections(sections, max_chars=max_chars)

    return build_document_chunks(
        document,
        chunk_content,
        chunk_id_factory=chunk_id_factory,
    )


def process_documents(
    documents: list[CanonicalDocument],
    *,
    preserve_block: PreservedBlockPredicate | None = None,
    excluded_section_headings: frozenset[str] = frozenset(),
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[DocumentChunk]:
    """Process eligible canonical documents in their supplied order."""

    return [
        chunk
        for document in documents
        for chunk in process_document(
            document,
            preserve_block=preserve_block,
            excluded_section_headings=excluded_section_headings,
            max_chars=max_chars,
        )
    ]
