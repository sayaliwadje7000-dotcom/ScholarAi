class OptimizationError(Exception):
    """Base exception for optimization operations."""


class OptimizationConfigurationError(OptimizationError):
    """Raised when optimization configuration is invalid."""


class CandidateEvaluationError(OptimizationError):
    """Raised when a candidate cannot be evaluated."""


class OptimizationValidationError(OptimizationError):
    """Raised when evaluation results fail validation."""


class OptimizationExecutionError(OptimizationError):
    """Raised when an optimization run cannot complete."""
