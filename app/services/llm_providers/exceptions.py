class LLMProviderError(Exception):
    """Base exception for LLM provider operations."""


class LLMProviderConfigurationError(LLMProviderError):
    """Provider configuration is invalid or incomplete."""


class LLMProviderExecutionError(LLMProviderError):
    """Provider execution failed."""


class LLMProviderUnavailableError(LLMProviderError):
    """Provider is temporarily unavailable."""


class LLMProviderAuthenticationError(LLMProviderError):
    """Provider authentication failed."""


class LLMAllProvidersFailedError(LLMProviderError):
    """All configured providers failed."""

    def __init__(
        self,
        message: str,
        attempts: list,
    ):

        super().__init__(message)

        self.attempts = attempts