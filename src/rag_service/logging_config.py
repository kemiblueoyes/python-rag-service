"""Configure logging for the rag_service package.

The handler is attached only to the rag_service logger. Provider SDK and
HTTP-client loggers keep their own levels. The package logger does not
propagate, so Uvicorn does not print the same application record again.
"""

import logging
import sys
from typing import TextIO

_LOGGER_NAME = "rag_service"
_HANDLER_NAME = "rag_service.diagnostics"
_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s "
    "operation=%(operation)s reason=%(reason)s %(message)s"
)


class _DiagnosticFilter(logging.Filter):
    """Supply operation and reason when a record does not set them."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "operation"):
            record.operation = "-"
        if not hasattr(record, "reason"):
            record.reason = "-"
        return True


def configure_logging(level: str, *, stream: TextIO | None = None) -> None:
    """Apply LOG_LEVEL to rag_service logging.

    Repeated calls update the level and formatter on the existing handler.
    They do not add another handler.
    """

    numeric = _LEVELS.get(level)
    if numeric is None:
        raise ValueError(
            "LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL."
        )

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(numeric)
    logger.propagate = False
    handler = _diagnostic_handler(logger)
    if handler is None:
        handler = logging.StreamHandler(
            stream if stream is not None else sys.stderr
        )
        handler.set_name(_HANDLER_NAME)
        handler.addFilter(_DiagnosticFilter())
        logger.addHandler(handler)
    elif stream is not None:
        handler.setStream(stream)
    handler.setLevel(numeric)
    handler.setFormatter(logging.Formatter(_FORMAT))


def _diagnostic_handler(
    logger: logging.Logger,
) -> logging.StreamHandler[TextIO] | None:
    for handler in logger.handlers:
        if handler.get_name() != _HANDLER_NAME:
            continue
        if isinstance(handler, logging.StreamHandler):
            return handler
    return None
