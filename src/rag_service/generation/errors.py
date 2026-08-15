class ContextBudgetError(ValueError):
    """Raised when the highest-ranked source exceeds the context budget."""

    def __init__(
        self,
        *,
        budget_tokens: int,
        required_tokens: int,
    ) -> None:
        self.budget_tokens = budget_tokens
        self.required_tokens = required_tokens

        super().__init__(
            "highest-ranked source exceeds the context token budget: "
            f"required {required_tokens}, "
            f"available {budget_tokens}"
        )
class LanguageModelError(RuntimeError):
    """Base error raised by language-model integrations."""


class LanguageModelProviderError(LanguageModelError):
    """Raised when the language-model provider request fails."""


class LanguageModelResponseError(LanguageModelError):
    """Raised when the provider returns no usable structured response."""


class LanguageModelRefusalError(LanguageModelResponseError):
    """Raised when the language model refuses the request."""