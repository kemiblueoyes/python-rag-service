from rag_service.connectors.wordpress.mapper import (
    WordPressMetadataMapping,
    map_wordpress_post,
)
from rag_service.connectors.wordpress.models import WordPressPost

AUDIENCE_LABELS = {
    "TW": "Technical Writer",
    "IA": "Information Architect",
    "DE": "Documentation Engineer",
    "KM": "Knowledge Manager",
    "DL": "Documentation Leader",
}


def test_maps_wordpress_post_to_canonical_document() -> None:
    post = WordPressPost.model_validate(
        {
            "id": 142,
            "date_gmt": "2026-07-17T14:00:00",
            "modified_gmt": "2026-07-18T10:30:00",
            "slug": "example-article",
            "status": "publish",
            "type": "post",
            "link": "https://example.com/example-article/",
            "title": {"rendered": "Example Article"},
            "content": {"rendered": "<p>Article content.</p>"},
            "categories": [4],
            "tags": [12],
            "acf": {
                "post_subtitle": "An example subtitle",
                "target_audience": ["Technical Writer"],
            },
        }
    )

    document = map_wordpress_post(
        post,
        metadata_mappings=(
            WordPressMetadataMapping(
                source="acf",
                source_key="post_subtitle",
                target_key="subtitle",
            ),
            WordPressMetadataMapping(
                source="acf",
                source_key="target_audience",
                target_key="audience",
            ),
        ),
    )

    assert document.document_id == "wordpress:post:142"
    assert document.source == "wordpress"
    assert document.source_id == "142"
    assert document.title == "Example Article"
    assert document.body == "<p>Article content.</p>"
    assert document.content_type == "post"
    assert document.indexable is True
    assert document.metadata["subtitle"] == "An example subtitle"
    assert document.metadata["audience"] == ["Technical Writer"]
    assert document.metadata["category_ids"] == [4]


def test_maps_yoast_schema_type_list() -> None:
    post = WordPressPost.model_validate(
        {
            "id": 101,
            "slug": "example-post",
            "status": "publish",
            "type": "post",
            "link": "https://example.com/example-post/",
            "title": {"rendered": "Example Post"},
            "content": {"rendered": "<p>Post content.</p>"},
            "yoast_head_json": {
                "schema": {
                    "@graph": [
                        {
                            "@type": ["Article", "BlogPosting"],
                            "wordCount": 750,
                            "inLanguage": "en-US",
                        }
                    ]
                }
            },
        }
    )

    document = map_wordpress_post(post)

    assert document.metadata["schema_type"] == "BlogPosting"
    assert document.metadata["word_count"] == 750
    assert document.metadata["language"] == "en-US"


def test_empty_page_is_non_indexable_landing_page() -> None:
    page = WordPressPost.model_validate(
        {
            "id": 12,
            "slug": "home",
            "status": "publish",
            "type": "page",
            "link": "https://example.com/",
            "title": {"rendered": "Home"},
            "content": {"rendered": ""},
        }
    )

    document = map_wordpress_post(page)

    assert document.document_role == "landing"
    assert document.indexable is False


def test_converts_audience_codes_to_labels() -> None:
    post = WordPressPost.model_validate(
        {
            "id": 102,
            "slug": "audience-example",
            "status": "publish",
            "type": "post",
            "link": "https://example.com/audience-example/",
            "title": {"rendered": "Audience Example"},
            "content": {"rendered": "<p>Post content.</p>"},
            "acf": {
                "target_audience": ["TW", "IA", "DE", "KM", "DL"],
            },
        }
    )

    document = map_wordpress_post(
        post,
        metadata_mappings=(
            WordPressMetadataMapping(
                source="acf",
                source_key="target_audience",
                target_key="audience",
                value_map=AUDIENCE_LABELS,
            ),
            WordPressMetadataMapping(
                source="acf",
                source_key="target_audience",
                target_key="audience_codes",
            ),
        ),
    )

    assert document.metadata["audience"] == [
        "Technical Writer",
        "Information Architect",
        "Documentation Engineer",
        "Knowledge Manager",
        "Documentation Leader",
    ]
    assert document.metadata["audience_codes"] == [
        "TW",
        "IA",
        "DE",
        "KM",
        "DL",
    ]


def test_preserves_multiple_values_from_wordpress_meta() -> None:
    post = WordPressPost.model_validate(
        {
            "id": 103,
            "slug": "products-example",
            "status": "publish",
            "type": "post",
            "link": "https://example.com/products-example/",
            "title": {"rendered": "Products Example"},
            "content": {"rendered": "<p>Post content.</p>"},
            "meta": {"applicable_products": ["editor", "api", "cli"]},
        }
    )

    document = map_wordpress_post(
        post,
        metadata_mappings=(
            WordPressMetadataMapping(
                source="meta",
                source_key="applicable_products",
                target_key="products",
            ),
        ),
    )

    assert document.metadata["products"] == ["editor", "api", "cli"]
