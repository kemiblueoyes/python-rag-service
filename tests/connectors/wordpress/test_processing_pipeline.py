import json
from pathlib import Path

from rag_service.connectors.wordpress.content_policy import (
    build_wordpress_block_preserver,
)
from rag_service.connectors.wordpress.mapper import map_wordpress_post
from rag_service.connectors.wordpress.models import WordPressPost
from rag_service.processing.pipeline import process_document

FIXTURE_PATH = (
    Path(__file__).parents[3]
    / "src/rag_service/connectors/wordpress/wp_json_api.json/child_page.json"
)
PRESERVE_WORDPRESS_ACCORDION = build_wordpress_block_preserver({"wp-block-accordion"})


def test_processes_real_wordpress_fixture_consistently() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    document = map_wordpress_post(WordPressPost.model_validate(payload[0]))

    first_run = process_document(
        document,
        preserve_block=PRESERVE_WORDPRESS_ACCORDION,
    )
    second_run = process_document(
        document,
        preserve_block=PRESERVE_WORDPRESS_ACCORDION,
    )

    assert first_run
    assert first_run == second_run
    assert [chunk.sequence for chunk in first_run] == list(range(len(first_run)))
    assert len({chunk.chunk_id for chunk in first_run}) == len(first_run)
    assert all(chunk.document_id == document.document_id for chunk in first_run)
    assert all(chunk.metadata == document.metadata for chunk in first_run)
    assert any(chunk.heading_path for chunk in first_run)
    assert any("table" in chunk.block_types for chunk in first_run)
    assert any(
        metadata.get("block_type") == "table" and "<table" in metadata["html"]
        for chunk in first_run
        for metadata in chunk.block_metadata
    )


def test_preserves_wordpress_accordion_as_one_chunk_block() -> None:
    record = WordPressPost.model_validate(
        {
            "id": 501,
            "slug": "accordion-example",
            "status": "publish",
            "type": "page",
            "link": "https://example.test/accordion-example/",
            "title": {"rendered": "Accordion Example"},
            "content": {
                "rendered": """
                    <h2 id="components">Components</h2>
                    <div class="wp-block-accordion">
                        <h3>Diagram title</h3>
                        <p>Diagram content.</p>
                    </div>
                """
            },
        }
    )
    document = map_wordpress_post(record)

    chunks = process_document(
        document,
        preserve_block=PRESERVE_WORDPRESS_ACCORDION,
        max_chars=10,
    )

    accordion_chunks = [chunk for chunk in chunks if "html_block" in chunk.block_types]
    assert len(accordion_chunks) == 1
    assert "Diagram title Diagram content." in accordion_chunks[0].text
    assert accordion_chunks[0].heading_path == ["Components"]
    assert accordion_chunks[0].block_metadata[0]["block_type"] == "html_block"
    assert "wp-block-accordion" in accordion_chunks[0].block_metadata[0]["html"]
