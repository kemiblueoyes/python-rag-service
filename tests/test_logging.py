import logging
import re
import sys
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from rag_service.api.app import app
from rag_service.api.startup import StartupConfigurationError
from rag_service.config import Settings, SettingsLoadError, load_settings, settings
from rag_service.logging_config import configure_logging

CANARY = "sk-secret-log-level"
_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


@pytest.fixture
def log_stream() -> StringIO:
    stream = StringIO()
    configure_logging("INFO", stream=stream)
    yield stream
    configure_logging(settings.log_level, stream=sys.stderr)


@pytest.mark.parametrize("level", _LEVELS)
def test_log_level_accepts_documented_values(level: str) -> None:
    loaded = Settings(log_level=level, _env_file=None)  # type: ignore[call-arg]

    assert loaded.log_level == level


@pytest.mark.parametrize("level", ["debug", "verbose", "", CANARY])
def test_invalid_log_level_uses_settings_diagnostics(
    level: str,
    log_stream: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", level)

    with caplog.at_level(logging.ERROR, logger="rag_service.config"):
        with pytest.raises(SettingsLoadError) as raised:
            load_settings()

    message = str(raised.value)
    assert "LOG_LEVEL" in message
    assert "DEBUG, INFO, WARNING, ERROR, or CRITICAL" in message
    rendered = log_stream.getvalue()
    assert "operation=settings" in rendered
    assert "reason=invalid_configuration" in rendered
    assert "LOG_LEVEL" in rendered
    if level:
        assert level not in message
        assert level not in rendered
        assert level not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_logging_format_includes_required_fields(log_stream: StringIO) -> None:
    logging.getLogger("rag_service.api.errors").error(
        "operation=%s reason=%s: %s",
        "startup",
        "invalid_configuration",
        "Check RAG_API_KEY.",
        extra={"operation": "startup", "reason": "invalid_configuration"},
    )

    line = log_stream.getvalue().strip()
    assert _TIMESTAMP.search(line)
    assert line.split(" ", 2)[2].startswith("ERROR rag_service.api.errors ")
    assert "operation=startup" in line
    assert "reason=invalid_configuration" in line
    assert "Check RAG_API_KEY." in line


def test_log_level_filters_lower_severity(log_stream: StringIO) -> None:
    logger = logging.getLogger("rag_service.api.errors")
    configure_logging("WARNING", stream=log_stream)
    logger.info(
        "operation=%s reason=%s: %s",
        "probe",
        "info_hidden",
        "hidden",
        extra={"operation": "probe", "reason": "info_hidden"},
    )
    logger.error(
        "operation=%s reason=%s: %s",
        "probe",
        "error_visible",
        "visible",
        extra={"operation": "probe", "reason": "error_visible"},
    )

    rendered = log_stream.getvalue()
    assert "info_hidden" not in rendered
    assert "error_visible" in rendered

    configure_logging("DEBUG", stream=log_stream)
    logger.debug(
        "operation=%s reason=%s: %s",
        "probe",
        "debug_visible",
        "visible",
        extra={"operation": "probe", "reason": "debug_visible"},
    )
    assert "debug_visible" in log_stream.getvalue()


def test_repeated_logging_setup_emits_one_line(log_stream: StringIO) -> None:
    configure_logging("INFO", stream=log_stream)
    configure_logging("ERROR", stream=log_stream)
    logging.getLogger("rag_service.config").error(
        "operation=%s reason=%s: %s",
        "settings",
        "invalid_configuration",
        "Check LOG_LEVEL.",
        extra={"operation": "settings", "reason": "invalid_configuration"},
    )

    assert log_stream.getvalue().count("\n") == 1
    diagnostic_handlers = [
        handler
        for handler in logging.getLogger("rag_service").handlers
        if handler.get_name() == "rag_service.diagnostics"
    ]
    assert len(diagnostic_handlers) == 1


def test_logging_does_not_propagate_or_enable_provider_debug(
    log_stream: StringIO,
) -> None:
    configure_logging("DEBUG", stream=log_stream)
    root_stream = StringIO()
    root_handler = logging.StreamHandler(root_stream)
    root_logger = logging.getLogger()
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_level = uvicorn_logger.level
    uvicorn_handlers = list(uvicorn_logger.handlers)
    root_logger.addHandler(root_handler)
    try:
        logging.getLogger("rag_service.api.errors").error(
            "operation=%s reason=%s: %s",
            "startup",
            "invalid_configuration",
            "Check RAG_API_KEY.",
            extra={"operation": "startup", "reason": "invalid_configuration"},
        )
        logging.getLogger("httpx").debug("provider-request-body sk-secret")
        logging.getLogger("openai").debug("provider-request-body sk-secret")
        logging.getLogger("voyageai").debug("provider-request-body sk-secret")
        logging.getLogger("qdrant_client").debug("provider-request-body sk-secret")
    finally:
        root_logger.removeHandler(root_handler)

    rendered = log_stream.getvalue()
    assert rendered.count("Check RAG_API_KEY.") == 1
    assert "provider-request-body" not in rendered
    assert "Check RAG_API_KEY." not in root_stream.getvalue()
    for name in ("httpx", "httpcore", "openai", "voyageai", "qdrant_client", "urllib3"):
        assert logging.getLogger(name).level == logging.NOTSET
    assert uvicorn_logger.level == uvicorn_level
    assert uvicorn_logger.handlers == uvicorn_handlers
    assert logging.getLogger("rag_service").propagate is False


def test_startup_validation_uses_the_application_log_format(
    log_stream: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "rag_api_key", None)
    monkeypatch.setattr(settings, "log_level", "INFO")

    with pytest.raises((StartupConfigurationError, ExceptionGroup)):
        with TestClient(app):
            pass

    rendered = log_stream.getvalue()
    assert _TIMESTAMP.search(rendered)
    assert "ERROR rag_service.api.startup " in rendered
    assert "operation=startup" in rendered
    assert "reason=invalid_configuration" in rendered
    assert "RAG_API_KEY" in rendered


def test_configure_logging_rejects_unknown_level_without_the_value() -> None:
    with pytest.raises(ValueError, match="LOG_LEVEL must be") as raised:
        configure_logging(CANARY)

    assert CANARY not in str(raised.value)
    assert "sk-secret" not in str(raised.value)
