from bs4 import Tag

# Add newly discovered WordPress component classes here. The generic parser
# will preserve any element containing at least one configured class.
WORDPRESS_PRESERVED_BLOCK_CLASSES: frozenset[str] = frozenset(
    {
        "wp-block-accordion",
    }
)


def is_preserved_wordpress_block(element: Tag) -> bool:
    """Return True for WordPress components that parsing must keep intact."""

    classes = {str(value) for value in element.get_attribute_list("class")}
    return not classes.isdisjoint(WORDPRESS_PRESERVED_BLOCK_CLASSES)
