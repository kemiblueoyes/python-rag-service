from unittest.mock import Mock

from rag_service.connectors.wordpress.client import WordPressClient
from rag_service.connectors.wordpress.connector import WordPressConnector
from rag_service.connectors.wordpress.models import WordPressPost
from rag_service.profiles.doc_landscape import DOC_LANDSCAPE_WORDPRESS_PROFILE


def make_page(
    page_id: int,
    title: str,
    *,
    parent: int = 0,
    acf: dict[str, object] | None = None,
) -> WordPressPost:
    slug = title.lower().replace(" ", "-")

    return WordPressPost.model_validate(
        {
            "id": page_id,
            "slug": slug,
            "status": "publish",
            "type": "page",
            "link": f"https://example.com/{slug}/",
            "title": {"rendered": title},
            "content": {"rendered": f"<p>{title} content.</p>"},
            "parent": parent,
            "acf": acf or {},
        }
    )


def test_enriches_series_landing_page_and_child() -> None:
    series_page = make_page(
        10,
        "Writing About AI",
        acf={
            "aeo_page_name": "Writing About AI Series",
            "aeo_page_description": ("Articles about documenting AI products."),
        },
    )
    child_page = make_page(
        11,
        "AI Assistants and Agents",
        parent=10,
    )

    client = Mock(spec=WordPressClient)
    client.fetch_all.return_value = [series_page, child_page]

    connector = WordPressConnector(
        client,
        profile=DOC_LANDSCAPE_WORDPRESS_PROFILE,
    )
    documents = connector.fetch_documents()

    documents_by_id = {document.source_id: document for document in documents}

    parent_document = documents_by_id["10"]
    child_document = documents_by_id["11"]

    assert parent_document.document_role == "landing"
    assert parent_document.metadata["page_role"] == "series_landing_page"
    assert parent_document.metadata["series_name"] == "Writing About AI Series"
    assert (
        parent_document.metadata["series_description"]
        == "Articles about documenting AI products."
    )

    assert child_document.document_role == "content"
    assert child_document.metadata["page_role"] == "series_article"
    assert child_document.metadata["series_name"] == "Writing About AI Series"
    assert (
        child_document.metadata["series_url"] == "https://example.com/writing-about-ai/"
    )
    assert child_document.metadata["parent_title"] == "Writing About AI"
    assert (
        child_document.metadata["parent_url"] == "https://example.com/writing-about-ai/"
    )


def test_enriches_nested_series_descendant() -> None:
    series_page = make_page(
        10,
        "Writing About AI",
        acf={
            "aeo_page_name": "Writing About AI Series",
        },
    )
    section_page = make_page(
        11,
        "AI Product Landscape",
        parent=10,
    )
    article_page = make_page(
        12,
        "AI Assistants and Agents",
        parent=11,
    )

    client = Mock(spec=WordPressClient)
    client.fetch_all.return_value = [
        series_page,
        section_page,
        article_page,
    ]

    connector = WordPressConnector(
        client,
        profile=DOC_LANDSCAPE_WORDPRESS_PROFILE,
    )
    documents = connector.fetch_documents()

    article_document = next(
        document for document in documents if document.source_id == "12"
    )

    assert article_document.metadata["parent_title"] == ("AI Product Landscape")
    assert article_document.metadata["series_name"] == ("Writing About AI Series")
    assert article_document.metadata["series_url"] == (
        "https://example.com/writing-about-ai/"
    )


def test_regular_page_is_not_marked_as_series_content() -> None:
    about_page = make_page(20, "About")

    client = Mock(spec=WordPressClient)
    client.fetch_all.return_value = [about_page]

    connector = WordPressConnector(client)
    documents = connector.fetch_documents()

    document = documents[0]

    assert document.document_role == "content"
    assert "page_role" not in document.metadata
    assert "series_name" not in document.metadata


def test_default_profile_preserves_hierarchy_without_series_semantics() -> None:
    parent_page = make_page(
        30,
        "Documentation",
        acf={"aeo_page_name": "Site-specific collection name"},
    )
    child_page = make_page(31, "Installation", parent=30)
    client = Mock(spec=WordPressClient)
    client.fetch_all.return_value = [parent_page, child_page]

    documents = WordPressConnector(client).fetch_documents()
    child_document = next(
        document for document in documents if document.source_id == "31"
    )

    assert child_document.metadata["parent_title"] == "Documentation"
    assert child_document.metadata["parent_url"] == (
        "https://example.com/documentation/"
    )
    assert "series_name" not in child_document.metadata


def test_doc_landscape_profile_maps_multiple_audiences() -> None:
    page = make_page(
        40,
        "Audience Example",
        acf={"target_audience": ["TW", "DL"]},
    )
    client = Mock(spec=WordPressClient)
    client.fetch_all.return_value = [page]

    document = WordPressConnector(
        client,
        profile=DOC_LANDSCAPE_WORDPRESS_PROFILE,
    ).fetch_documents()[0]

    assert document.metadata["audience"] == [
        "Technical Writer",
        "Documentation Leader",
    ]
    assert document.metadata["audience_codes"] == ["TW", "DL"]
