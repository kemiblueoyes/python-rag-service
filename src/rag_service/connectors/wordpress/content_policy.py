from collections.abc import Callable, Collection

from bs4 import Tag


def build_wordpress_block_preserver(
    preserved_classes: Collection[str],
) -> Callable[[Tag], bool]:
    """Build a predicate that preserves configured WordPress HTML blocks."""

    configured_classes = frozenset(preserved_classes)

    def is_preserved_wordpress_block(element: Tag) -> bool:
        classes = {str(value) for value in element.get_attribute_list("class")}
        return not classes.isdisjoint(configured_classes)

    return is_preserved_wordpress_block
