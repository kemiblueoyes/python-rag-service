"""Fixed input limits for the public search and answer API."""

QUERY_MAX_CHARACTERS = 2_000
FILTER_VALUE_MAX_CHARACTERS = 256
FILTER_LIST_MAX_ENTRIES = 50
SEARCH_LIMIT_MIN = 1
SEARCH_LIMIT_MAX = 20
SEARCH_LIMIT_DEFAULT = 5
REQUEST_BODY_MAX_BYTES = 64 * 1024

CAPABILITY_PATHS = frozenset({"/v1/search", "/v1/answer"})

REQUEST_TOO_LARGE_CODE = "request_too_large"
REQUEST_TOO_LARGE_MESSAGE = "The request body is too large."

REQUEST_TOO_LARGE_RESPONSE = {
    "error": {
        "code": REQUEST_TOO_LARGE_CODE,
        "message": REQUEST_TOO_LARGE_MESSAGE,
        "details": [],
    }
}
