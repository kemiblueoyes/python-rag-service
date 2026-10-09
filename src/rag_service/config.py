import logging
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Literal, NoReturn, get_args

from dotenv.parser import parse_stream
from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict, SettingsError

from rag_service.logging_config import configure_logging


class Settings(BaseSettings):
    app_name: str = "python-rag-service"
    environment: str = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # API authentication
    rag_api_key: SecretStr | None = None

    # WordPress connector
    wordpress_base_url: str | None = None
    wordpress_api_path: str = "/wp-json/wp/v2"
    wordpress_request_timeout: float = 10.0
    wordpress_page_size: int = 100
    wordpress_collections: tuple[str, ...] = ("posts", "pages")
    wordpress_profile: str = "default"

    # Embeddings
    embedding_provider: str = "voyage"
    embedding_model: str = "voyage-4-lite"
    embedding_dimension: int = 1024
    embedding_batch_size: int = 128
    voyage_api_key: str | None = None
    voyage_timeout_seconds: float = Field(default=60.0, gt=0, allow_inf_nan=False)
    voyage_max_retries: int = Field(default=0, ge=0, le=2)

    # Vector storage
    vector_database: str = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "rag_chunks"
    qdrant_timeout_seconds: int = Field(default=5, ge=1)

    # Retrieval
    lexical_corpus_path: Path = Path("data/wordpress-chunks.json")

    retrieval_vector_candidate_depth: int = 20
    retrieval_lexical_candidate_depth: int = 20
    retrieval_fused_candidate_depth: int = 20
    retrieval_rrf_k: int = 60
    retrieval_support_cutoff: float = 0.70

    # Reranking
    reranking_provider: str = "voyage"
    reranking_model: str = "rerank-2.5"

    # Answer generation
    generation_enabled: bool = True
    generation_provider: Literal["openai"] = "openai"
    generation_model: str = "gpt-5.6-terra"
    generation_reasoning_effort: Literal[
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    ] = "low"
    generation_context_budget_tokens: int = 8_000
    generation_max_output_tokens: int = 1_000
    openai_api_key: str | None = None
    openai_timeout_seconds: float = Field(default=120.0, gt=0, allow_inf_nan=False)
    openai_max_retries: int = Field(default=0, ge=0, le=2)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


logger = logging.getLogger(__name__)

_SETTINGS_ERROR_FIELD = re.compile(
    r'error (?:parsing|getting) value for field "([^"]+)"'
)
_BOOL_ERROR_TYPES = frozenset({"bool_parsing", "bool_type"})
_INT_ERROR_TYPES = frozenset({"int_parsing", "int_type", "int_from_float"})
_FLOAT_ERROR_TYPES = frozenset({"float_parsing", "float_type", "float_from_int"})


@dataclass(frozen=True, slots=True)
class SettingsLoadFailure:
    """One setting or file that could not be loaded."""

    setting: str
    message: str


class SettingsLoadError(RuntimeError):
    """Raised when environment values or `.env` cannot be loaded safely."""

    def __init__(self, failures: tuple[SettingsLoadFailure, ...]) -> None:
        self.failures = failures
        summary = "; ".join(
            f"{failure.setting}: {failure.message}" for failure in failures
        )
        super().__init__(summary)


def load_settings() -> Settings:
    """Load settings from the environment and `.env`.

    A malformed value or an unreadable `.env` line raises SettingsLoadError.
    The error names the setting and the correction. It omits supplied values,
    settings dictionaries, raw parser exceptions, and exception chains.
    Missing optional values keep their defaults so imports and OpenAPI
    generation still work. Invalid values are not replaced with defaults.
    """

    configure_logging("INFO")
    file_failures = _dotenv_failures()
    if file_failures:
        _reject_settings(file_failures)

    try:
        loaded = Settings()
    except ValidationError as exc:
        _reject_settings(_validation_failures(exc))
    except SettingsError as exc:
        _reject_settings(_settings_error_failures(exc))
    configure_logging(loaded.log_level)
    return loaded


def _reject_settings(failures: list[SettingsLoadFailure]) -> NoReturn:
    for failure in failures:
        logger.error(
            "operation=settings reason=invalid_configuration setting=%s: %s",
            failure.setting,
            failure.message,
            extra={
                "operation": "settings",
                "reason": "invalid_configuration",
                "setting": failure.setting,
            },
        )
    raise SettingsLoadError(tuple(failures)) from None


def _dotenv_failures() -> list[SettingsLoadFailure]:
    failures: list[SettingsLoadFailure] = []
    for path in _env_files():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            failures.append(
                SettingsLoadFailure(
                    ".env",
                    "Save this file as UTF-8 text.",
                )
            )
            continue
        except OSError:
            failures.append(
                SettingsLoadFailure(
                    ".env",
                    "Make this file readable.",
                )
            )
            continue

        try:
            bindings = list(parse_stream(StringIO(text)))
        except Exception:
            failures.append(
                SettingsLoadFailure(
                    ".env",
                    "Fix the unreadable statement. Use NAME=value.",
                )
            )
            continue

        for binding in bindings:
            if binding.error:
                failures.append(
                    SettingsLoadFailure(
                        ".env",
                        "Fix the unreadable statement at line "
                        f"{binding.original.line}. Use NAME=value.",
                    )
                )
    return failures


def _env_files() -> list[Path]:
    configured = Settings.model_config.get("env_file")
    if configured is None:
        return []
    if isinstance(configured, (str, Path)):
        return [Path(configured)]
    return [Path(item) for item in configured]


def _validation_failures(exc: ValidationError) -> list[SettingsLoadFailure]:
    failures: list[SettingsLoadFailure] = []
    for error in exc.errors():
        loc = error.get("loc", ())
        field_name = next(
            (part for part in loc if isinstance(part, str)),
            None,
        )
        error_type = error.get("type")
        kind = error_type if isinstance(error_type, str) else ""
        failures.append(
            SettingsLoadFailure(
                _env_name(field_name),
                _correction(field_name, kind),
            )
        )
    if not failures:
        failures.append(
            SettingsLoadFailure(
                "settings",
                "Fix the invalid environment values.",
            )
        )
    return failures


def _settings_error_failures(exc: SettingsError) -> list[SettingsLoadFailure]:
    match = _SETTINGS_ERROR_FIELD.search(str(exc))
    field_name = match.group(1) if match else None
    if field_name == "wordpress_collections":
        message = "Set this value to a JSON array of strings."
    elif field_name is None:
        message = "Fix the invalid environment value or .env entry."
    else:
        message = _correction(field_name, "")
    return [SettingsLoadFailure(_env_name(field_name), message)]


_TIMEOUT_CORRECTIONS = {
    "voyage_timeout_seconds": (
        "Set this value to a finite number of seconds greater than 0."
    ),
    "openai_timeout_seconds": (
        "Set this value to a finite number of seconds greater than 0."
    ),
    "qdrant_timeout_seconds": (
        "Set this value to a whole number of seconds of at least 1."
    ),
}
_RETRY_CORRECTION = "Set this value to an integer from 0 through 2."
_RETRY_FIELDS = frozenset({"voyage_max_retries", "openai_max_retries"})


def _correction(field_name: str | None, error_type: str) -> str:
    if field_name in _TIMEOUT_CORRECTIONS:
        return _TIMEOUT_CORRECTIONS[field_name]
    if field_name in _RETRY_FIELDS:
        return _RETRY_CORRECTION
    if error_type in _BOOL_ERROR_TYPES:
        return "Set this value to true or false."
    if error_type in _INT_ERROR_TYPES:
        return "Set this value to an integer."
    if error_type in _FLOAT_ERROR_TYPES:
        return "Set this value to a number."
    if error_type == "literal_error":
        options = _literal_options(field_name)
        if options:
            return f"Set this value to {_join_options(options)}."
    if field_name == "wordpress_collections":
        return "Set this value to a JSON array of strings."
    return "Set this value to a valid value for this setting."


def _literal_options(field_name: str | None) -> tuple[str, ...] | None:
    if field_name is None or field_name not in Settings.model_fields:
        return None
    annotation = Settings.model_fields[field_name].annotation
    if annotation is None or get_args(annotation) == ():
        return None
    origin = getattr(annotation, "__origin__", None)
    if origin is not Literal:
        return None
    args = get_args(annotation)
    if not all(isinstance(arg, str) for arg in args):
        return None
    return args


def _join_options(options: tuple[str, ...]) -> str:
    if len(options) == 1:
        return options[0]
    if len(options) == 2:
        return f"{options[0]} or {options[1]}"
    return ", ".join(options[:-1]) + f", or {options[-1]}"


def _env_name(field_name: str | None) -> str:
    if field_name is None or field_name not in Settings.model_fields:
        return "settings"
    field = Settings.model_fields[field_name]
    if isinstance(field.alias, str):
        return field.alias
    return field_name.upper()


settings = load_settings()
