"""Typed failures for centralized evaluation execution."""


class EvaluationError(Exception):
    """Base exception for evaluation infrastructure."""


class DuplicateEvaluatorError(EvaluationError):
    """An evaluator identifier is already registered."""


class UnknownEvaluatorError(EvaluationError):
    """No evaluator is registered for the requested identifier."""


class InvalidEvaluatorInputError(EvaluationError):
    """The supplied evaluator input is invalid."""


class InvalidEvaluationTransitionError(EvaluationError):
    """A lifecycle transition is not permitted."""


class EvaluationExecutionError(EvaluationError):
    """An evaluator failed during execution."""


class EvaluationTimeoutError(EvaluationExecutionError):
    """An evaluator exceeded its configured timeout."""