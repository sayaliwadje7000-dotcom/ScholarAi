class EmbeddingError(Exception):
    """Base exception for embedding operations."""


class EmbeddingConfigurationError(EmbeddingError):
    pass


class EmbeddingAuthenticationError(EmbeddingError):
    pass


class EmbeddingRateLimitError(EmbeddingError):
    pass


class EmbeddingTimeoutError(EmbeddingError):
    pass


class EmbeddingProviderError(EmbeddingError):
    pass


class EmbeddingValidationError(EmbeddingError):
    pass


class EmbeddingInputTooLargeError(EmbeddingValidationError):
    pass
