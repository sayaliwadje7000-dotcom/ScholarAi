class ExperimentError(Exception):
    """Base exception for experiment management."""


class ExperimentValidationError(ExperimentError):
    """Raised when experiment data is invalid."""


class ExperimentNotFoundError(ExperimentError):
    """Raised when an experiment cannot be found."""


class DuplicateExperimentError(ExperimentError):
    """Raised when an experiment ID already exists."""


class ExperimentComparisonError(ExperimentError):
    """Raised when experiment comparison cannot be completed."""
