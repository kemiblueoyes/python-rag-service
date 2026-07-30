import httpx2
import pytest

from rag_service.connectors.wordpress.client import WordPressClient


def make_wordpress_record(
    record_id: int,
    record_type: str = "post",
) -> dict[str, object]:
    return {
        "id": record_id,
        "slug": f"article-{record_id}",
        "status": "publish",
        "type": record_type,
        "link": f"https://example.com/article-{record_id}/",
        "title": {"rendered": f"Article {record_id}"},
        "content": {"rendered": f"<p>Content {record_id}</p>"},
    }


def test_fetch_posts_handles_pagination() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)

        assert request.url.path == "/wp-json/wp/v2/posts"
        assert request.url.params["status"] == "publish"
        assert request.url.params["per_page"] == "2"

        page = request.url.params["page"]

        if page == "1":
            return httpx2.Response(
                200,
                headers={"X-WP-TotalPages": "2"},
                json=[
                    make_wordpress_record(1),
                    make_wordpress_record(2),
                ],
            )

        return httpx2.Response(
            200,
            headers={"X-WP-TotalPages": "2"},
            json=[make_wordpress_record(3)],
        )

    transport = httpx2.MockTransport(handler)

    with httpx2.Client(transport=transport) as http_client:
        client = WordPressClient(
            base_url="https://example.com",
            page_size=2,
            http_client=http_client,
        )

        posts = client.fetch_posts()

    assert [post.id for post in posts] == [1, 2, 3]
    assert len(requests) == 2


def test_fetch_all_retrieves_supported_content_types() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        endpoint = request.url.path.rsplit("/", maxsplit=1)[-1]

        if endpoint == "posts":
            payload = [make_wordpress_record(1, "post")]
        elif endpoint == "pages":
            payload = [make_wordpress_record(2, "page")]
        elif endpoint == "glossary":
            payload = [make_wordpress_record(3, "glossary")]
        else:
            return httpx2.Response(404)

        return httpx2.Response(
            200,
            headers={"X-WP-TotalPages": "1"},
            json=payload,
        )

    transport = httpx2.MockTransport(handler)

    with httpx2.Client(transport=transport) as http_client:
        client = WordPressClient(
            base_url="https://example.com",
            http_client=http_client,
        )

        records = client.fetch_all()

    assert [record.type for record in records] == ["post", "page", "glossary"]
    assert [record.id for record in records] == [1, 2, 3]


def test_fetch_collection_raises_for_http_error() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            500,
            json={"message": "WordPress server error"},
        )

    transport = httpx2.MockTransport(handler)

    with httpx2.Client(transport=transport) as http_client:
        client = WordPressClient(
            base_url="https://example.com",
            http_client=http_client,
        )

        with pytest.raises(httpx2.HTTPStatusError):
            client.fetch_posts()


def test_fetch_collection_rejects_non_list_response() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={"id": 1},
        )

    transport = httpx2.MockTransport(handler)

    with httpx2.Client(transport=transport) as http_client:
        client = WordPressClient(
            base_url="https://example.com",
            http_client=http_client,
        )

        with pytest.raises(
            ValueError,
            match="Expected a list from WordPress endpoint",
        ):
            client.fetch_posts()