from dataclasses import dataclass

from rag_service.models.document import CanonicalDocument


@dataclass
class DocumentChanges:
    """Results of comparing two indexing runs."""

    new: list[CanonicalDocument]
    updated: list[CanonicalDocument]
    unchanged: list[CanonicalDocument]
    removed: list[CanonicalDocument]


def detect_document_changes(
    current_documents: list[CanonicalDocument],
    previous_documents: list[CanonicalDocument],
) -> DocumentChanges:
    """Compare the current documents with the previous indexing run."""

    current_by_id = {
        document.document_id: document
        for document in current_documents
    }
    previous_by_id = {
        document.document_id: document
        for document in previous_documents
    }

    new: list[CanonicalDocument] = []
    updated: list[CanonicalDocument] = []
    unchanged: list[CanonicalDocument] = []

    for current_document in current_documents:
        previous_document = previous_by_id.get(
            current_document.document_id
        )

        if previous_document is None:
            new.append(current_document)
            continue

        if (
            current_document.model_dump(mode="json")
            != previous_document.model_dump(mode="json")
        ):
            updated.append(current_document)
        else:
            unchanged.append(current_document)

    removed = [
        previous_document
        for previous_document in previous_documents
        if previous_document.document_id not in current_by_id
    ]

    return DocumentChanges(
        new=new,
        updated=updated,
        unchanged=unchanged,
        removed=removed,
    )