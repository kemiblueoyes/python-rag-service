from typing import Any, Literal

from rag_service.models.canonical_document import CanonicalDocument

from .models import WordPressPost

AUDIENCE_LABELS = {
    "TW": "Technical Writer",
    "IA": "Information Architect",
    "DE": "Documentation Engineer",
    "KM": "Knowledge Manager",
    "DL": "Documentation Leader",
}

def _extract_schema_metadata(
    yoast_head_json: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract useful document-level metadata from Yoast JSON-LD."""

    if not yoast_head_json:
        return {}

    metadata: dict[str, Any] = {}

    description = yoast_head_json.get("description")
    if description:
        metadata["description"] = description

    schema = yoast_head_json.get("schema", {})
    graph = schema.get("@graph", [])

    if not isinstance(graph, list):
        return metadata

    for node in graph:
        if not isinstance(node, dict):
            continue

        raw_node_type = node.get("@type")

        if isinstance(raw_node_type, str):
            node_types = {raw_node_type}
        elif isinstance(raw_node_type, list):
            node_types = {
                value
                for value in raw_node_type
                if isinstance(value, str)
            }
        else:
            node_types = set()

        article_types = {"Article", "TechArticle", "BlogPosting"}

        if node_types & article_types:
            for preferred_type in (
                "TechArticle",
                "BlogPosting",
                "Article",
            ):
                if preferred_type in node_types:
                    metadata["schema_type"] = preferred_type
                    break

            metadata["word_count"] = node.get("wordCount")
            metadata["language"] = node.get("inLanguage")

            audience = node.get("audience", [])
            metadata["audience"] = [
                item["audienceType"]
                for item in audience
                if isinstance(item, dict) and item.get("audienceType")
            ]

        elif "WebPage" in node_types:
            metadata.setdefault("language", node.get("inLanguage"))

            if node.get("wordCount") is not None:
                metadata.setdefault("word_count", node.get("wordCount"))

    return metadata


def map_wordpress_post(post: WordPressPost) -> CanonicalDocument:
    """Convert a WordPress REST API record into a canonical document."""

    metadata: dict[str, Any] = {
        "slug": post.slug,
        "author_id": post.author,
        "featured_media_id": post.featured_media,
        "category_ids": post.categories,
        "tag_ids": post.tags,
        "parent_id": post.parent,
        "menu_order": post.menu_order,
    }

    subtitle = post.acf.get("post_subtitle")
    if subtitle:
        metadata["subtitle"] = subtitle

    target_audience = post.acf.get("target_audience", [])

    if target_audience:
        metadata["audience"] = [
            AUDIENCE_LABELS.get(value, value)
            for value in target_audience
        ]
        metadata["audience_codes"] = target_audience

    aeo_page_name = post.acf.get("aeo_page_name")
    if aeo_page_name:
        metadata["aeo_page_name"] = aeo_page_name

    aeo_page_description = post.acf.get("aeo_page_description")
    if aeo_page_description:
        metadata["aeo_page_description"] = aeo_page_description

    schema_metadata = _extract_schema_metadata(post.yoast_head_json)

    # Prefer the original ACF audience values when both sources provide them.
    if "audience" in metadata:
        schema_metadata.pop("audience", None)

    metadata.update(schema_metadata)

    has_body_content = bool(post.content.rendered.strip())

    document_role: Literal["content", "landing", "archive"] = (
        "landing"
        if post.type == "page" and not has_body_content
        else "content"
    )

    indexable = post.status == "publish" and has_body_content

    return CanonicalDocument(
        document_id=f"wordpress:{post.type}:{post.id}",
        source="wordpress",
        source_id=str(post.id),
        title=post.title.rendered,
        url=post.link,
        body=post.content.rendered,
        content_type=post.type,
        document_role=document_role,
        indexable=indexable,
        metadata=metadata,
        published_at=post.date_gmt,
        modified_at=post.modified_gmt,
    )