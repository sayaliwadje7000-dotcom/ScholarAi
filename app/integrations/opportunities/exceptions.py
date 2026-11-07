class OpportunityProviderError(Exception):
    pass


class OpportunityProviderConfigurationError(OpportunityProviderError):
    pass


class OpportunityProviderAuthenticationError(OpportunityProviderError):
    pass


class OpportunityProviderRateLimitError(OpportunityProviderError):
    pass


class OpportunityProviderTimeoutError(OpportunityProviderError):
    pass


class OpportunityProviderUnavailableError(OpportunityProviderError):
    pass


class OpportunityProviderResponseError(OpportunityProviderError):
    pass


class OpportunityProviderValidationError(OpportunityProviderError):
    pass


class OpportunityProviderDisabledError(OpportunityProviderError):
    pass