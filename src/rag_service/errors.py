class ServiceConfigurationError(Exception):
    """A known configuration problem found while handling a request.

    The diagnostic is a fixed instruction. It does not include request
    content, credentials, or provider exception text.
    """

    def __init__(self, *, operation: str, reason: str, diagnostic: str) -> None:
        self.operation = operation
        self.reason = reason
        self.diagnostic = diagnostic
        super().__init__(diagnostic)
