from rag_service.connectors.wordpress.mapper import map_wordpress_post
from rag_service.connectors.wordpress.models import WordPressPost


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
                "subtitle": "An example subtitle",
                "target_audience": ["Technical Writer"],
            },
        }
    )

    document = map_wordpress_post(post)

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