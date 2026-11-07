class ResourceProviderError(Exception):
    """Base exception for external resource providers."""


class ResourceProviderConfigurationError(
    ResourceProviderError
):
    pass


class ResourceProviderAuthenticationError(
    ResourceProviderError
):
    pass


class ResourceProviderRateLimitError(
    ResourceProviderError
):
    pass


class ResourceProviderTimeoutError(
    ResourceProviderError
):
    pass


class ResourceProviderUnavailableError(
    ResourceProviderError
):
    pass


class ResourceProviderResponseError(
    ResourceProviderError
):
    pass


class ResourceProviderValidationError(
    ResourceProviderError
):
    pass


class ResourceProviderDisabledError(
    ResourceProviderError
):
    pass