from rag_service.connectors.wordpress.connector import WordPressConnectorProfile

from .doc_landscape import DOC_LANDSCAPE_WORDPRESS_PROFILE

WORDPRESS_PROFILES = {
    "default": WordPressConnectorProfile(),
    "doc_landscape": DOC_LANDSCAPE_WORDPRESS_PROFILE,
}


def get_wordpress_profile(name: str) -> WordPressConnectorProfile:
    """Return a configured WordPress profile by name."""

    try:
        return WORDPRESS_PROFILES[name]
    except KeyError as error:
        available = ", ".join(sorted(WORDPRESS_PROFILES))
        raise ValueError(
            f"Unknown WordPress profile {name!r}. Available profiles: {available}"
        ) from error
