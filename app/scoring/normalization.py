import math

from app.scoring.exceptions import ScoringInputError


def normalize_score(value: float) -> float:
    if isinstance(value, bool):
        raise ScoringInputError("Boolean values are not valid scores.")

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ScoringInputError("Score must be numeric.")

    if not math.isfinite(number):
        raise ScoringInputError("Score must be finite.")

    return max(0.0, min(1.0, number))


def normalize_text(value: str) -> str:
    if not isinstance(value, str):
        raise ScoringInputError("Text input must be a string.")

    return " ".join(value.casefold().split())