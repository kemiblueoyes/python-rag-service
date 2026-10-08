"""Validate local API configuration before the service accepts traffic.

These checks read settings and the local chunk file. They do not call
Voyage, OpenAI, Qdrant, or WordPress, and they do not run at import time.
"""

import ipaddress
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr, ValidationError

from rag_service.config import Settings
from rag_service.lexical import load_lexical_corpus

logger = logging.getLogger(__name__)

_SUPPORTED_EMBEDDING_PROVIDERS = frozenset({"voyage"})
_SUPPORTED_RERANKING_PROVIDERS = frozenset({"voyage"})
_SUPPORTED_VECTOR_DATABASES = frozenset({"qdrant"})
_QDRANT_SCHEMES = frozenset({"http", "https"})
_QDRANT_URL_MESSAGE = (
    "Set this value to an HTTP or HTTPS URL with a host "
    "and an optional port from 1 through 65535."
)
_HOST_LABEL = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")
_DOTTED_QUAD = re.compile(r"^\d+(?:\.\d+){3}$")


@dataclass(frozen=True, slots=True)
class ConfigurationFailure:
    """One local setting or file that failed startup validation."""

    setting: str
    message: str


class StartupConfigurationError(RuntimeError):
    """Raised when local API configuration is invalid."""

    def __init__(self, failures: tuple[ConfigurationFailure, ...]) -> None:
        self.failures = failures
        summary = "; ".join(
            f"{failure.setting}: {failure.message}" for failure in failures
        )
        super().__init__(summary)


def validate_api_configuration(current: Settings) -> None:
    """Reject API settings that cannot serve indexed content.

    Logs the setting name and a fixed instruction. The log and the
    raised error omit setting values, credentials, corpus content, and
    raw parser or validation exceptions.
    """

    failures = _collect_failures(current)
    if not failures:
        return

    for failure in failures:
        logger.error(
            "operation=startup reason=invalid_configuration setting=%s: %s",
            failure.setting,
            failure.message,
            extra={
                "operation": "startup",
                "reason": "invalid_configuration",
                "setting": failure.setting,
            },
        )

    raise StartupConfigurationError(tuple(failures))


def _collect_failures(current: Settings) -> list[ConfigurationFailure]:
    failures: list[ConfigurationFailure] = []

    if _secret_is_blank(current.rag_api_key):
        _add(
            failures,
            "RAG_API_KEY",
            "Set this value to a non-empty string.",
        )

    if current.embedding_provider not in _SUPPORTED_EMBEDDING_PROVIDERS:
        _add(
            failures,
            "EMBEDDING_PROVIDER",
            "Set this value to voyage.",
        )

    if _is_blank(current.embedding_model):
        _add(
            failures,
            "EMBEDDING_MODEL",
            "Set this value to a non-empty model name.",
        )

    # Qdrant stores this value as the collection vector size.
    if current.embedding_dimension < 1:
        _add(
            failures,
            "EMBEDDING_DIMENSION",
            "Set this value to an integer of at least 1.",
        )

    if _is_blank(current.voyage_api_key):
        _add(
            failures,
            "VOYAGE_API_KEY",
            "Set this value to a non-empty string.",
        )

    if current.vector_database not in _SUPPORTED_VECTOR_DATABASES:
        _add(
            failures,
            "VECTOR_DATABASE",
            "Set this value to qdrant.",
        )

    if _is_blank(current.qdrant_url):
        _add(
            failures,
            "QDRANT_URL",
            "Set this value to a non-empty URL.",
        )
    else:
        url_message = _qdrant_url_message(current.qdrant_url)
        if url_message is not None:
            _add(failures, "QDRANT_URL", url_message)

    if _is_blank(current.qdrant_collection):
        _add(
            failures,
            "QDRANT_COLLECTION",
            "Set this value to a non-empty collection name.",
        )

    if current.reranking_provider not in _SUPPORTED_RERANKING_PROVIDERS:
        _add(
            failures,
            "RERANKING_PROVIDER",
            "Set this value to voyage.",
        )

    if _is_blank(current.reranking_model):
        _add(
            failures,
            "RERANKING_MODEL",
            "Set this value to a non-empty model name.",
        )

    # Bounds match RetrievalService.
    _require_at_least_one(
        failures,
        current.retrieval_vector_candidate_depth,
        "RETRIEVAL_VECTOR_CANDIDATE_DEPTH",
    )
    _require_at_least_one(
        failures,
        current.retrieval_lexical_candidate_depth,
        "RETRIEVAL_LEXICAL_CANDIDATE_DEPTH",
    )
    _require_at_least_one(
        failures,
        current.retrieval_fused_candidate_depth,
        "RETRIEVAL_FUSED_CANDIDATE_DEPTH",
    )
    _require_at_least_one(
        failures,
        current.retrieval_rrf_k,
        "RETRIEVAL_RRF_K",
    )

    if not 0.0 <= current.retrieval_support_cutoff <= 1.0:
        _add(
            failures,
            "RETRIEVAL_SUPPORT_CUTOFF",
            "Set this value to a number from 0 through 1.",
        )

    if current.generation_enabled:
        _validate_generation(current, failures)

    _validate_corpus(current.lexical_corpus_path, failures)
    return failures


def _validate_generation(
    current: Settings,
    failures: list[ConfigurationFailure],
) -> None:
    """Check answer-generation settings used when generation is on.

    Token bounds match ContextAssembler and OpenAILanguageModel.
    """

    if _is_blank(current.generation_model):
        _add(
            failures,
            "GENERATION_MODEL",
            "Set this value to a non-empty model name.",
        )

    if current.generation_context_budget_tokens < 1:
        _add(
            failures,
            "GENERATION_CONTEXT_BUDGET_TOKENS",
            "Set this value to an integer of at least 1.",
        )

    if current.generation_max_output_tokens < 1:
        _add(
            failures,
            "GENERATION_MAX_OUTPUT_TOKENS",
            "Set this value to an integer of at least 1.",
        )

    if _is_blank(current.openai_api_key):
        _add(
            failures,
            "OPENAI_API_KEY",
            "Set this value to a non-empty string, or set GENERATION_ENABLED to false.",
        )


def _validate_corpus(
    path: Path,
    failures: list[ConfigurationFailure],
) -> None:
    """Load the chunk file with the existing corpus loader."""

    setting = "LEXICAL_CORPUS_PATH"

    if not path.is_file():
        _add(failures, setting, "Point this setting to a readable file.")
        return

    if not os.access(path, os.R_OK):
        _add(failures, setting, "Make this file readable.")
        return

    try:
        chunks = load_lexical_corpus(path)
    except UnicodeDecodeError:
        _add(failures, setting, "Store valid JSON in this file.")
    except json.JSONDecodeError:
        _add(failures, setting, "Store valid JSON in this file.")
    except ValidationError:
        _add(failures, setting, "Fix the invalid chunk record in this file.")
    except ValueError:
        _add(failures, setting, "Store a JSON list of chunks in this file.")
    except OSError:
        _add(failures, setting, "Make this file readable.")
    else:
        if not chunks:
            _add(failures, setting, "Add at least one chunk to this file.")


def _require_at_least_one(
    failures: list[ConfigurationFailure],
    value: int,
    setting: str,
) -> None:
    if value < 1:
        _add(failures, setting, "Set this value to an integer of at least 1.")


def _add(
    failures: list[ConfigurationFailure],
    setting: str,
    message: str,
) -> None:
    failures.append(ConfigurationFailure(setting, message))


def _qdrant_url_message(value: str) -> str | None:
    """Return a fixed diagnostic when a Qdrant URL is syntactically invalid.

    Parsing uses the standard library only. It does not resolve DNS or
    open a connection, and the diagnostic does not include the URL.
    """

    if any(character.isspace() for character in value):
        return _QDRANT_URL_MESSAGE

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except (UnicodeError, ValueError):
        return _QDRANT_URL_MESSAGE

    if parsed.scheme.lower() not in _QDRANT_SCHEMES:
        return _QDRANT_URL_MESSAGE
    if hostname is None or not _valid_qdrant_host(hostname):
        return _QDRANT_URL_MESSAGE
    if port is not None and not 1 <= port <= 65535:
        return _QDRANT_URL_MESSAGE
    return None


def _valid_qdrant_host(hostname: str) -> bool:
    if _DOTTED_QUAD.fullmatch(hostname):
        try:
            ipaddress.IPv4Address(hostname)
        except ValueError:
            return False
        return True

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        return True

    name = hostname[:-1] if hostname.endswith(".") else hostname
    if not name or len(name) > 253:
        return False
    return all(_HOST_LABEL.fullmatch(label) for label in name.split("."))


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _secret_is_blank(value: SecretStr | None) -> bool:
    if value is None:
        return True
    return not value.get_secret_value().strip()
