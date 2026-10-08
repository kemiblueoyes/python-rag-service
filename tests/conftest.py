import logging
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def capture_service_logs(
    caplog: pytest.LogCaptureFixture,
) -> Iterator[None]:
    """Capture rag_service records when that logger does not propagate."""

    service_logger = logging.getLogger("rag_service")
    service_logger.addHandler(caplog.handler)
    yield
    service_logger.removeHandler(caplog.handler)
