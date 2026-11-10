class FinalEvaluationError(Exception):
    """Base exception for final evaluation operations."""


class DuplicateEvaluationError(FinalEvaluationError):
    """Raised when an evaluation is registered more than once."""


class EvaluationNotFoundError(FinalEvaluationError):
    """Raised when a requested evaluation is not registered."""


class InvalidEvaluationError(FinalEvaluationError):
    """Raised when an evaluation definition is invalid."""


class EvaluationExecutionError(FinalEvaluationError):
    """Raised when the evaluation runner cannot execute."""
