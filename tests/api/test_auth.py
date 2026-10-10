import hashlib

import pytest
from pydantic import SecretStr

from rag_service.api.auth import (
    APIAuthenticationConfigurationError,
    InvalidAPIKeyError,
    require_api_key,
)
from rag_service.config import settings

CONFIGURED_KEY = "test-api-key"


def test_require_api_key_accepts_matching_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr("test-api-key"),
    )

    require_api_key("test-api-key")


def test_require_api_key_rejects_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr("test-api-key"),
    )

    with pytest.raises(InvalidAPIKeyError):
        require_api_key(None)


@pytest.mark.parametrize(
    "supplied_key",
    [
        "test-api-ke",
        "wrong-api-ky",
        "test-api-key-extra",
        "",
        "test-api-key ",
        " test-api-key",
        "test-api-key\n",
    ],
)
def test_require_api_key_rejects_incorrect_key(
    monkeypatch: pytest.MonkeyPatch,
    supplied_key: str,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr(CONFIGURED_KEY),
    )

    length_delta = {
        "test-api-ke": -1,
        "wrong-api-ky": 0,
        "test-api-key-extra": 1,
    }
    if supplied_key in length_delta:
        assert (len(supplied_key) > len(CONFIGURED_KEY)) - (
            len(supplied_key) < len(CONFIGURED_KEY)
        ) == length_delta[supplied_key]

    with pytest.raises(InvalidAPIKeyError):
        require_api_key(supplied_key)


def test_require_api_key_accepts_exact_whitespace_and_multibyte_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for configured_key in ("test-api-key\n", "cl\u00e9-api-key"):
        monkeypatch.setattr(
            settings,
            "rag_api_key",
            SecretStr(configured_key),
        )

        require_api_key(configured_key)


def test_require_api_key_rejects_different_unicode_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr("caf\u00e9-key"),
    )

    with pytest.raises(InvalidAPIKeyError):
        require_api_key("cafe\u0301-key")


def test_present_keys_reach_compare_digest_as_sha256_digests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compared: list[tuple[bytes, bytes]] = []

    def capture_compare(left: bytes, right: bytes) -> bool:
        compared.append((left, right))
        return left == right

    monkeypatch.setattr(
        "rag_service.api.auth.compare_digest",
        capture_compare,
    )
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr(CONFIGURED_KEY),
    )

    require_api_key(CONFIGURED_KEY)
    with pytest.raises(InvalidAPIKeyError):
        require_api_key("wrong-api-key")

    assert len(compared) == 2
    expected_configured = hashlib.sha256(
        CONFIGURED_KEY.encode("utf-8")
    ).digest()
    for supplied_key, (left, right) in zip(
        (CONFIGURED_KEY, "wrong-api-key"),
        compared,
        strict=True,
    ):
        assert left == hashlib.sha256(supplied_key.encode("utf-8")).digest()
        assert right == expected_configured
        assert len(left) == 32
        assert len(right) == 32


def test_missing_key_does_not_reach_compare_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_compare(_left: bytes, _right: bytes) -> bool:
        raise AssertionError("compare_digest should not run")

    monkeypatch.setattr(
        "rag_service.api.auth.compare_digest",
        reject_compare,
    )
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        SecretStr(CONFIGURED_KEY),
    )

    with pytest.raises(InvalidAPIKeyError):
        require_api_key(None)


@pytest.mark.parametrize(
    "configured_key",
    [None, SecretStr("")],
)
def test_require_api_key_rejects_missing_configuration(
    monkeypatch: pytest.MonkeyPatch,
    configured_key: SecretStr | None,
) -> None:
    monkeypatch.setattr(
        settings,
        "rag_api_key",
        configured_key,
    )

    with pytest.raises(APIAuthenticationConfigurationError):
        require_api_key("test-api-key")