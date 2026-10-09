"""Close provider clients without logging exception text."""

import logging

logger = logging.getLogger(__name__)


def close_client(resource: object, *, operation: str) -> None:
    """Call close() when a resource has one.

    A failure writes one diagnostic. The log omits the exception text,
    the traceback, and any provider response.
    """

    closer = getattr(resource, "close", None)
    if not callable(closer):
        return
    try:
        closer()
    except Exception:
        logger.error(
            "operation=%s reason=cleanup_failed: "
            "The service could not close a provider client.",
            operation,
            extra={"operation": operation, "reason": "cleanup_failed"},
        )
