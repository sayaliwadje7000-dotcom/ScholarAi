class ResourceDiscoveryError(Exception):
    """
    Base exception for educational resource discovery.
    """


class ResourceDiscoveryValidationError(
    ResourceDiscoveryError
):
    """
    Raised when discovery input or configuration is invalid.
    """


class ResourceDiscoveryProviderError(
    ResourceDiscoveryError
):
    """
    Raised when an individual provider search fails.
    """


class ResourceDiscoveryUnavailableError(
    ResourceDiscoveryError
):
    """
    Raised when no configured provider can complete
    the requested discovery operation.
    """


class ResourceDiscoveryResponseError(
    ResourceDiscoveryError
):
    """
    Raised when a provider returns invalid resource data.
    """