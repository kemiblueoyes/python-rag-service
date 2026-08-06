from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from rag_service.models.canonical_document import CanonicalDocument

from .models import WordPressPost


@dataclass(frozen=True)
class WordPressMetadataMapping:
    """Map a custom WordPress field into canonical document metadata."""

    source: Literal["acf", "meta"]
    source_key: str
    target_key: str
    value_map: Mapping[str, str] | None = None


def _map_custom_value(
    value: Any,
    value_map: Mapping[str, str] | None,
) -> Any:
    """Translate scalar or list values without changing their shape."""

    if value_map is None:
        return value

    if isinstance(value, list):
        return [
            value_map.get(item, item) if isinstance(item, str) else item
            for item in value
        ]

    if isinstance(value, str):
        return value_map.get(value, value)

    return value


def _extract_custom_metadata(
    post: WordPressPost,
    mappings: Sequence[WordPressMetadataMapping],
) -> dict[str, Any]:
    """Extract configured ACF or REST metadata fields."""

    metadata: dict[str, Any] = {}

    for mapping in mappings:
        source_fields = post.acf if mapping.source == "acf" else post.meta

        if mapping.source_key not in source_fields:
            continue

        metadata[mapping.target_key] = _map_custom_value(
            source_fields[mapping.source_key],
            mapping.value_map,
        )

    return metadata


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
            node_types = {value for value in raw_node_type if isinstance(value, str)}
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


def map_wordpress_post(
    post: WordPressPost,
    metadata_mappings: Sequence[WordPressMetadataMapping] = (),
) -> CanonicalDocument:
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

    schema_metadata = _extract_schema_metadata(post.yoast_head_json)
    metadata.update(schema_metadata)
    metadata.update(_extract_custom_metadata(post, metadata_mappings))

    has_body_content = bool(post.content.rendered.strip())

    document_role: Literal["content", "landing", "archive"] = (
        "landing" if post.type == "page" and not has_body_content else "content"
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
