from typing import Protocol


class TokenCounter(Protocol):
    """Count tokens using rules compatible with the selected language model."""

    def count_tokens(self, text: str) -> int:
        """Return the number of tokens in the supplied text."""

        ...