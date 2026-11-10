class ScoringError(Exception):
    """Base exception for scoring operations."""


class ScoringConfigurationError(ScoringError):
    """Raised when scoring configuration is invalid."""


class ScoringInputError(ScoringError):
    """Raised when scoring inputs are invalid."""


class ScorerNotFoundError(ScoringError):
    """Raised when a requested scorer is not registered."""