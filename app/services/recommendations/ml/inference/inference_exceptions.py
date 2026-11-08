"""Exceptions raised during recommendation inference."""


class InferenceError(Exception):
    """Base exception for ML inference failures."""


class InferenceInputError(InferenceError):
    """Raised when inference input is invalid."""


class ModelNotAvailableError(InferenceError):
    """Raised when a trained model is unavailable."""


class ModelCompatibilityError(InferenceError):
    """Raised when model and transformer are incompatible."""


class PredictionError(InferenceError):
    """Raised when model prediction fails."""