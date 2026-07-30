from rag_service.connectors.wordpress.models import WordPressPost


def test_wordpress_post_parses_rest_api_response() -> None:
    response = {
        "id": 142,
        "date_gmt": "2026-07-17T14:00:00",
        "modified_gmt": "2026-07-18T10:30:00",
        "slug": "when-retrieval-fails",
        "status": "publish",
        "type": "post",
        "link": "https://example.com/when-retrieval-fails/",
        "title": {
            "rendered": "When Retrieval Fails",
        },
        "content": {
            "rendered": "<p>Retrieval can fail for several reasons.</p>",
        },
        "excerpt": {
            "rendered": "<p>An introduction to retrieval failures.</p>",
        },
        "author": 1,
        "featured_media": 25,
        "categories": [4, 8],
        "tags": [12, 15],
        "meta": {
            "target_audience": "technical writers",
        },
    }

    post = WordPressPost.model_validate(response)

    assert post.id == 142
    assert post.type == "post"
    assert post.title.rendered == "When Retrieval Fails"
    assert post.content.rendered.startswith("<p>")
    assert post.categories == [4, 8]
    assert post.tags == [12, 15]
    assert post.meta["target_audience"] == "technical writers"


def test_wordpress_page_uses_defaults_for_optional_fields() -> None:
    response = {
        "id": 25,
        "date_gmt": "2026-07-10T12:00:00",
        "modified_gmt": "2026-07-10T12:00:00",
        "slug": "about",
        "status": "publish",
        "type": "page",
        "link": "https://example.com/about/",
        "title": {
            "rendered": "About",
        },
        "content": {
            "rendered": "<p>About this site.</p>",
        },
        "parent": 0,
        "menu_order": 0,
    }

    page = WordPressPost.model_validate(response)

    assert page.type == "page"
    assert page.parent == 0
    assert page.menu_order == 0
    assert page.categories == []
    assert page.tags == []
    assert page.meta == {}

def test_wordpress_post_parses_custom_metadata() -> None:
    response = {
        "id": 142,
        "slug": "example-article",
        "status": "publish",
        "type": "post",
        "link": "https://example.com/example-article/",
        "title": {"rendered": "Example Article"},
        "content": {"rendered": "<p>Article content.</p>"},
        "acf": {
            "subtitle": "A useful article subtitle",
            "target_audience": [
                "Technical Writer",
                "Documentation Engineer",
            ],
        },
        "yoast_head_json": {
            "description": "A description of the article.",
            "schema": {
                "@context": "https://schema.org",
                "@graph": [],
            },
        },
    }

    post = WordPressPost.model_validate(response)

    assert post.acf["subtitle"] == "A useful article subtitle"
    assert post.acf["target_audience"] == [
        "Technical Writer",
        "Documentation Engineer",
    ]
    assert post.yoast_head_json is not None
    assert (
        post.yoast_head_json["description"]
        == "A description of the article."
    )