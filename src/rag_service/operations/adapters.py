"""Fixed operations; HTTP clients cannot choose configuration or paths."""

from pathlib import Path
from typing import Any

from rag_service.client_lifecycle import close_client
from rag_service.commands import evaluate_retrieval, index_wordpress
from rag_service.config import settings
from rag_service.embeddings import create_embedding_provider
from rag_service.vectorstores import create_vector_store

RUNS_DIRECTORY = Path("data/operations/runs")
DOCUMENT_PATH = Path("data/wordpress-documents.json")


def index(_job_id: str) -> dict[str, Any]:
    owned: list[object] = []
    try:
        embedding = create_embedding_provider(settings)
        owned.append(embedding)
        vectors = create_vector_store(settings)
        owned.append(vectors)
        result = index_wordpress.run(
            DOCUMENT_PATH,
            settings.lexical_corpus_path,
            embedding_provider=embedding,
            vector_store=vectors,
            embedding_batch_size=settings.embedding_batch_size,
        )
        changes = result.changes
        counts = {
            name: len(getattr(changes, name))
            for name in ("new", "updated", "unchanged", "removed")
        }
        stats = result.vector_index
        if stats is None:
            raise RuntimeError("Missing vector outcome")
        return {
            **counts,
            "changes_detected": any(
                counts[name] for name in ("new", "updated", "removed")
            ),
            "documents_indexed": stats.documents_indexed,
            "chunks_indexed": stats.chunks_indexed,
            "documents_cleared": stats.documents_deleted,
            "artifact_paths": {
                "documents": str(DOCUMENT_PATH),
                "chunks": str(settings.lexical_corpus_path),
            },
        }
    finally:
        for resource in reversed(owned):
            close_client(resource, operation="index_wordpress")


def evaluate(job_id: str) -> dict[str, Any]:
    directory = RUNS_DIRECTORY / job_id
    json_path = directory / "retrieval_baseline.json"
    markdown_path = directory / "retrieval_baseline.md"
    report = evaluate_retrieval.run(
        evaluate_retrieval.DATASET_PATH, json_path, markdown_path
    )
    return {
        "dataset_id": report["dataset_id"],
        "dataset_version": report["dataset_version"],
        "generated_at": report["generated_at"],
        "summary": report["summary"],
        "failed_case_ids": [
            case["case_id"] for case in report["cases"] if not case["passed"]
        ],
        "report_paths": {"json": str(json_path), "markdown": str(markdown_path)},
        "retrieval_configuration": {
            "collection": report["collection"],
            "k": report["k"],
            **{
                name: str(getattr(settings, name))
                if name == "lexical_corpus_path"
                else getattr(settings, name)
                for name in (
                    "embedding_provider",
                    "embedding_model",
                    "embedding_dimension",
                    "vector_database",
                    "lexical_corpus_path",
                    "reranking_provider",
                    "reranking_model",
                    "retrieval_vector_candidate_depth",
                    "retrieval_lexical_candidate_depth",
                    "retrieval_fused_candidate_depth",
                    "retrieval_rrf_k",
                    "retrieval_support_cutoff",
                )
            },
        },
    }
