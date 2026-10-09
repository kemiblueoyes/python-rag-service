import logging
from unittest.mock import Mock

from rag_service.connectors.wordpress.connector import WordPressConnector
from rag_service.connectors.wordpress.mapper import map_wordpress_post
from rag_service.connectors.wordpress.models import WordPressPost
from rag_service.processing.pipeline import process_documents
from rag_service.profiles.doc_landscape import DOC_LANDSCAPE_WORDPRESS_PROFILE

SECRET = "s3cret-token"
REJECTED_URLS = (
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    "data:text/html,hello",
    "ftp://example.com/file",
    " https://example.com/spaced",
    "https://exa mple.com/spaced",
    "https://",
    "/docs/relative",
    "example.com/docs",
    "http://user@example.com/only-user",
    f"https://user:{SECRET}@example.com/private",
    "https://@example.com/empty-user",
)


def wordpress_post(
    record_id: int,
    link: str,
    *,
    parent: int = 0,
    acf: dict[str, object] | None = None,
    body: str = "<p>Body text.</p>",
) -> WordPressPost:
    return WordPressPost.model_validate(
        {
            "id": record_id,
            "slug": f"record-{record_id}",
            "status": "publish",
            "type": "page",
            "link": link,
            "title": {"rendered": f"Record {record_id}"},
            "content": {"rendered": body},
            "parent": parent,
            "acf": acf or {},
        }
    )


def test_indexes_http_and_https_source_urls() -> None:
    documents = [
        map_wordpress_post(
            wordpress_post(1, "http://example.com/http-doc")
        ),
        map_wordpress_post(
            wordpress_post(2, "HTTPS://example.com/https-doc")
        ),
    ]

    chunks = process_documents(documents)

    assert [document.indexable for document in documents] == [True, True]
    assert [chunk.url for chunk in chunks] == [
        "http://example.com/http-doc",
        "HTTPS://example.com/https-doc",
    ]
    assert [chunk.document_id for chunk in chunks] == [
        "wordpress:page:1",
        "wordpress:page:2",
    ]


def test_rejected_source_urls_produce_no_chunks(
    caplog: logging.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        documents = [
            map_wordpress_post(wordpress_post(index + 10, url))
            for index, url in enumerate(REJECTED_URLS)
        ]
        chunks = process_documents(documents)

    assert chunks == []
    assert all(document.indexable is False for document in documents)
    assert SECRET not in caplog.text
    assert "javascript:" not in caplog.text
    assert "example.com/private" not in caplog.text
    assert "only-user" not in caplog.text
    for index, _url in enumerate(REJECTED_URLS):
        record_id = index + 10
        assert f"record_id={record_id}" in caplog.text
    assert "invalid_source_url" in caplog.text


def test_one_rejected_url_leaves_the_other_document_indexed(
    caplog: logging.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        documents = [
            map_wordpress_post(
                wordpress_post(3, f"https://user:{SECRET}@example.com/private")
            ),
            map_wordpress_post(
                wordpress_post(4, "https://example.com/kept")
            ),
        ]
        chunks = process_documents(documents)

    assert [chunk.document_id for chunk in chunks] == ["wordpress:page:4"]
    assert chunks[0].url == "https://example.com/kept"
    assert documents[0].indexable is False
    assert documents[1].indexable is True
    assert SECRET not in caplog.text
    assert "record_id=3" in caplog.text


def test_rejected_parent_and_series_urls_are_not_stored_on_chunks(
    caplog: logging.LogCaptureFixture,
) -> None:
    parent = wordpress_post(
        20,
        "javascript:alert(1)",
        acf={
            "aeo_page_name": "Series name",
            "aeo_page_description": "Series description",
        },
    )
    child = wordpress_post(
        21,
        "https://example.com/child/",
        parent=20,
    )
    client = Mock()
    client.fetch_all.return_value = [parent, child]
    connector = WordPressConnector(
        client,
        profile=DOC_LANDSCAPE_WORDPRESS_PROFILE,
    )

    with caplog.at_level(logging.WARNING):
        documents = connector.fetch_documents()
        chunks = process_documents(documents)

    child_document = next(
        document for document in documents if document.source_id == "21"
    )
    assert child_document.indexable is True
    assert child_document.metadata["parent_title"] == "Record 20"
    assert "parent_url" not in child_document.metadata
    assert "series_url" not in child_document.metadata
    assert [chunk.document_id for chunk in chunks] == ["wordpress:page:21"]
    assert chunks[0].url == "https://example.com/child/"
    assert "parent_url" not in chunks[0].metadata
    assert "series_url" not in chunks[0].metadata
    assert "javascript:" not in caplog.text
    assert "record_id=20" in caplog.text
