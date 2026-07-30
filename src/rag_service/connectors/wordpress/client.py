import httpx2

from .models import WordPressPost


class WordPressClient:
    """Retrieve post-like records from the WordPress REST API."""

    def __init__(
        self,
        base_url: str,
        api_path: str = "/wp-json/wp/v2",
        timeout: float = 10.0,
        page_size: int = 100,
        http_client: httpx2.Client | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("A WordPress base URL is required.")

        self.api_base_url = (
            f"{base_url.rstrip('/')}/{api_path.strip('/')}"
        )
        self.page_size = page_size
        self._owns_client = http_client is None
        self._client = http_client or httpx2.Client(timeout=timeout)

    def fetch_collection(self, endpoint: str) -> list[WordPressPost]:
        """Retrieve every published record from a REST collection."""

        records: list[WordPressPost] = []
        page = 1

        while True:
            response = self._client.get(
                f"{self.api_base_url}/{endpoint.strip('/')}",
                params={
                    "status": "publish",
                    "per_page": self.page_size,
                    "page": page,
                },
            )
            response.raise_for_status()

            payload = response.json()

            if not isinstance(payload, list):
                raise ValueError(
                    f"Expected a list from WordPress endpoint: {endpoint}"
                )

            records.extend(
                WordPressPost.model_validate(item)
                for item in payload
            )

            total_pages = int(
                response.headers.get("X-WP-TotalPages", "1")
            )

            if page >= total_pages:
                break

            page += 1

        return records

    def fetch_posts(self) -> list[WordPressPost]:
        return self.fetch_collection("posts")

    def fetch_pages(self) -> list[WordPressPost]:
        return self.fetch_collection("pages")

    def fetch_glossary(self) -> list[WordPressPost]:
        return self.fetch_collection("glossary")

    def fetch_all(self) -> list[WordPressPost]:
        return (
            self.fetch_posts()
            + self.fetch_pages()
            + self.fetch_glossary()
    )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()