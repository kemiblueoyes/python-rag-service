from rag_service.models.canonical_document import CanonicalDocument
from rag_service.processing.identifiers import StableChunkIdFactory
from rag_service.processing.models import ChunkContent, ContentBlock


def make_document(document_id: str = "example:article:42") -> CanonicalDocument:
    return CanonicalDocument(
        document_id=document_id,
        source="example",
        source_id="article-42",
        title="Retrieval Guide",
        url="https://docs.example.test/retrieval",
        body="<p>Source body.</p>",
        content_type="article",
        metadata={"language": "en-US"},
    )


def make_chunk(
    text: str = "Retrieve relevant content.",
    heading_path: list[str] | None = None,
    anchor: str | None = "retrieval",
) -> ChunkContent:
    return ChunkContent(
        text=text,
        heading_path=heading_path or ["Guide", "Retrieval"],
        blocks=[ContentBlock(block_type="paragraph", text=text)],
        anchor=anchor,
    )


def test_generates_the_same_id_during_reindexing() -> None:
    document = make_document()
    chunk = make_chunk()

    first_id = StableChunkIdFactory()(document, chunk, 0)
    second_id = StableChunkIdFactory()(document, chunk, 0)

    assert first_id == second_id
    assert first_id.startswith("example:article:42:chunk:v1:")


def test_sequence_changes_do_not_change_chunk_id() -> None:
    document = make_document()
    chunk = make_chunk()

    first_id = StableChunkIdFactory()(document, chunk, 0)
    shifted_id = StableChunkIdFactory()(document, chunk, 12)

    assert first_id == shifted_id


def test_content_heading_or_document_changes_change_chunk_id() -> None:
    original_id = StableChunkIdFactory()(make_document(), make_chunk(), 0)

    changed_text_id = StableChunkIdFactory()(
        make_document(),
        make_chunk(text="Different content."),
        0,
    )
    changed_heading_id = StableChunkIdFactory()(
        make_document(),
        make_chunk(heading_path=["Guide", "Indexing"]),
        0,
    )
    changed_document_id = StableChunkIdFactory()(
        make_document(document_id="example:article:99"),
        make_chunk(),
        0,
    )

    assert (
        len({original_id, changed_text_id, changed_heading_id, changed_document_id})
        == 4
    )


def test_non_identity_metadata_does_not_change_chunk_id() -> None:
    original_document = make_document()
    updated_document = original_document.model_copy(
        update={
            "title": "Renamed Retrieval Guide",
            "metadata": {"language": "fr-FR"},
        }
    )
    original_chunk = make_chunk(anchor="retrieval")
    updated_chunk = make_chunk(anchor="renamed-retrieval")

    original_id = StableChunkIdFactory()(original_document, original_chunk, 0)
    updated_id = StableChunkIdFactory()(updated_document, updated_chunk, 0)

    assert original_id == updated_id


def test_identical_chunks_get_unique_deterministic_ids() -> None:
    document = make_document()
    chunk = make_chunk()

    first_run = StableChunkIdFactory()
    first_ids = [first_run(document, chunk, sequence) for sequence in range(2)]

    second_run = StableChunkIdFactory()
    second_ids = [second_run(document, chunk, sequence) for sequence in range(2)]

    assert first_ids == second_ids
    assert first_ids[0] != first_ids[1]
    assert first_ids[1].endswith(":duplicate:2")
