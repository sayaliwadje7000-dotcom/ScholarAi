class OpportunityValidityError(Exception):
    """Base exception for opportunity validity evaluation."""


class OpportunityEligibilityError(OpportunityValidityError):
    """Raised when eligibility evaluation receives invalid input."""


class OpportunityDeadlineError(OpportunityValidityError):
    """Raised when deadline evaluation receives invalid input."""


class OpportunityFreshnessError(OpportunityValidityError):
    """Raised when freshness evaluation receives invalid input."""


class OpportunityValidityConfigurationError(OpportunityValidityError):
    """Raised when validity configuration is invalid."""