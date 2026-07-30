from rag_service.indexing.change_detection import (
    detect_document_changes,
)
from rag_service.models.document import CanonicalDocument


def make_document(
    source_id: str,
    *,
    title: str,
    indexable: bool = True,
) -> CanonicalDocument:
    return CanonicalDocument(
        document_id=f"wordpress:page:{source_id}",
        source="wordpress",
        source_id=source_id,
        title=title,
        url=f"https://example.com/page-{source_id}/",
        body=f"<p>{title} content.</p>",
        content_type="page",
        indexable=indexable,
    )


def test_detects_document_changes() -> None:
    unchanged_document = make_document(
        "1",
        title="Unchanged Page",
    )
    previous_updated_document = make_document(
        "2",
        title="Old Title",
    )
    current_updated_document = make_document(
        "2",
        title="New Title",
    )
    new_document = make_document(
        "3",
        title="New Page",
    )
    removed_document = make_document(
        "4",
        title="Removed Page",
    )

    changes = detect_document_changes(
        current_documents=[
            unchanged_document,
            current_updated_document,
            new_document,
        ],
        previous_documents=[
            unchanged_document,
            previous_updated_document,
            removed_document,
        ],
    )

    assert [
        document.source_id
        for document in changes.new
    ] == ["3"]

    assert [
        document.source_id
        for document in changes.updated
    ] == ["2"]

    assert [
        document.source_id
        for document in changes.unchanged
    ] == ["1"]

    assert [
        document.source_id
        for document in changes.removed
    ] == ["4"]


def test_indexability_change_is_detected_as_update() -> None:
    previous_document = make_document(
        "1",
        title="Landing Page",
        indexable=True,
    )
    current_document = make_document(
        "1",
        title="Landing Page",
        indexable=False,
    )

    changes = detect_document_changes(
        current_documents=[current_document],
        previous_documents=[previous_document],
    )

    assert changes.updated == [current_document]
    assert changes.unchanged == []