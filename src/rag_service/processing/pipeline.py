from rag_service.models.canonical_document import CanonicalDocument
from rag_service.models.chunk import DocumentChunk
from rag_service.processing.chunk_metadata import build_document_chunks
from rag_service.processing.chunker import DEFAULT_MAX_CHARS, chunk_sections
from rag_service.processing.heading_hierarchy import build_heading_sections
from rag_service.processing.html_parser import PreservedBlockPredicate, parse_html
from rag_service.processing.identifiers import ChunkIdFactory


def process_document(
    document: CanonicalDocument,
    *,
    preserve_block: PreservedBlockPredicate | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
    chunk_id_factory: ChunkIdFactory | None = None,
) -> list[DocumentChunk]:
    """Transform one canonical content document into retrieval-ready chunks."""

    if not document.indexable or document.document_role != "content":
        return []

    blocks = parse_html(document.body, preserve_block=preserve_block)
    sections = build_heading_sections(blocks)
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
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[DocumentChunk]:
    """Process eligible canonical documents in their supplied order."""

    return [
        chunk
        for document in documents
        for chunk in process_document(
            document,
            preserve_block=preserve_block,
            max_chars=max_chars,
        )
    ]
