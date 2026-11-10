from collections.abc import Sequence


def validate_non_empty(values, name="values"):
    if values is None:
        raise ValueError(f"{name} cannot be None.")

    if isinstance(values, (str, bytes)):
        if not values:
            raise ValueError(f"{name} cannot be empty.")
        return values

    if not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence.")

    if len(values) == 0:
        raise ValueError(f"{name} cannot be empty.")

    return values


def validate_same_length(y_true, y_pred):
    validate_non_empty(y_true, "y_true")
    validate_non_empty(y_pred, "y_pred")

    if len(y_true) != len(y_pred):
        raise ValueError(
            "y_true and y_pred must have equal lengths."
        )


def validate_positive_k(k):
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer.")

    return k


def validate_relevance_values(values):
    validate_non_empty(values, "relevance")

    for value in values:
        if isinstance(value, bool):
            raise ValueError("Relevance values must be numeric.")

        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(
                "Relevance values must be non-negative numbers."
            )

    return values


def validate_probability(value, name="value"):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric.")

    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric.")

    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1.")

    return float(value)