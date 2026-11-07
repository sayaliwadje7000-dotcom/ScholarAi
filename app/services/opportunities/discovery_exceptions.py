class OpportunityDiscoveryError(Exception):
    """
    Base exception for opportunity discovery operations.
    """


class OpportunityDiscoveryUnavailableError(
    OpportunityDiscoveryError
):
    """
    Raised when no usable opportunity provider is available.
    """


class OpportunityDiscoveryValidationError(
    OpportunityDiscoveryError
):
    """
    Raised when discovery inputs or provider selection
    are invalid.
    """


class OpportunityDiscoveryResponseError(
    OpportunityDiscoveryError
):
    """
    Raised when a provider returns invalid opportunity data.
    """


class OpportunityDiscoveryConfigurationError(
    OpportunityDiscoveryError
):
    """
    Raised when the provider registry is incorrectly configured.
    """