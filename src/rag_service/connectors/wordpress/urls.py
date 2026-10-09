"""Checks for WordPress document URLs stored on indexed chunks."""

import logging
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)


def is_absolute_http_url(value: object) -> bool:
    """Return whether a value is an absolute http or https URL.

    The check parses the string locally. It does not resolve a host or
    open a connection. A username, a password, or an empty userinfo
    slot makes the URL invalid.
    """

    if not isinstance(value, str) or value == "":
        return False
    if any(character.isspace() or ord(character) < 32 for character in value):
        return False

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError:
        return False

    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    if parsed.username or parsed.password or "@" in parsed.netloc:
        return False
    if parsed.netloc == "" or not hostname:
        return False
    return True


def log_rejected_source_url(record_id: int) -> None:
    """Log one diagnostic for a WordPress record that will not be indexed.

    The record ID is the WordPress numeric ID. The message does not
    include the URL or any credentials.
    """

    logger.warning(
        "operation=index_wordpress reason=invalid_source_url record_id=%s: "
        "A WordPress record was not indexed because its source URL "
        "is not an absolute HTTP or HTTPS URL without credentials.",
        record_id,
        extra={
            "operation": "index_wordpress",
            "reason": "invalid_source_url",
        },
    )
