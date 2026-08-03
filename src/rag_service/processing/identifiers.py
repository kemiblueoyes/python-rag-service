import hashlib
import json
from collections import defaultdict
from collections.abc import Callable

from rag_service.models.canonical_document import CanonicalDocument
from rag_service.processing.models import ChunkContent

CHUNK_ID_VERSION = 1

ChunkIdFactory = Callable[[CanonicalDocument, ChunkContent, int], str]


class StableChunkIdFactory:
    """Build stable chunk IDs from document and chunk content.

    The same content always yields the same ID. Create a new factory for each
    document so duplicate chunks can be numbered in order; that numbering stays
    stable as long as chunk order does not change.
    """

    def __init__(self) -> None:
        self._occurrences: dict[str, int] = defaultdict(int)

    def __call__(
        self,
        document: CanonicalDocument,
        chunk: ChunkContent,
        sequence: int,
    ) -> str:
        del sequence  # Sequence is intentionally excluded from stable identity.

        digest = _chunk_digest(document, chunk)
        occurrence = self._occurrences[digest]
        self._occurrences[digest] += 1

        base_id = f"{document.document_id}:chunk:v{CHUNK_ID_VERSION}:{digest}"
        if occurrence == 0:
            return base_id
        return f"{base_id}:duplicate:{occurrence + 1}"


def _chunk_digest(document: CanonicalDocument, chunk: ChunkContent) -> str:
    identity = {
        "document_id": document.document_id,
        "heading_path": chunk.heading_path,
        "text": chunk.text,
        "version": CHUNK_ID_VERSION,
    }
    serialized = json.dumps(
        identity,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
