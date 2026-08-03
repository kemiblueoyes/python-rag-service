from rag_service.models.canonical_document import CanonicalDocument
from rag_service.processing.pipeline import process_document, process_documents


def make_document(
    document_id: str = "example:article:42",
    *,
    body: str = "<h2 id='overview'>Overview</h2><p>Content.</p>",
    indexable: bool = True,
    document_role: str = "content",
) -> CanonicalDocument:
    return CanonicalDocument.model_validate(
        {
            "document_id": document_id,
            "source": "example",
            "source_id": document_id.rsplit(":", 1)[-1],
            "title": "Example document",
            "url": "https://docs.example.test/example",
            "body": body,
            "content_type": "article",
            "indexable": indexable,
            "document_role": document_role,
            "metadata": {"language": "en-US"},
        }
    )


def test_processes_canonical_document_end_to_end() -> None:
    document = make_document(
        body="""
        <h1>Guide</h1>
        <h2 id="retrieval">Retrieval</h2>
        <p>Retrieve relevant content.</p>
        <ul><li>Embed the query</li><li>Search the index</li></ul>
        """
    )

    chunks = process_document(document, max_chars=100)

    assert len(chunks) == 1
    assert chunks[0].document_id == document.document_id
    assert chunks[0].heading_path == ["Guide", "Retrieval"]
    assert chunks[0].anchor == "retrieval"
    assert chunks[0].block_types == ["paragraph", "list"]
    assert chunks[0].metadata == {"language": "en-US"}
    assert chunks[0].sequence == 0
    assert chunks[0].chunk_id.startswith("example:article:42:chunk:v1:")


def test_skips_non_indexable_and_non_content_documents() -> None:
    documents = [
        make_document("example:article:1", indexable=False),
        make_document("example:article:2", document_role="landing"),
        make_document("example:article:3"),
    ]

    chunks = process_documents(documents)

    assert {chunk.document_id for chunk in chunks} == {"example:article:3"}


def test_reprocessing_produces_identical_chunks() -> None:
    document = make_document()

    first_run = process_document(document)
    second_run = process_document(document)

    assert first_run == second_run
