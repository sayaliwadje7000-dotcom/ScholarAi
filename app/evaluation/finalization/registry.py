from collections.abc import Callable
from typing import Any

from app.evaluation.finalization.exceptions import (
    DuplicateEvaluationError,
    EvaluationNotFoundError,
    InvalidEvaluationError,
)


Evaluator = Callable[[], dict[str, Any]]


class FinalEvaluationRegistry:
    """
    Registry for system-wide evaluation components.

    Existing evaluation modules can be integrated through callable adapters.
    """

    def __init__(self) -> None:
        self._evaluators: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        category: str,
        evaluator: Evaluator,
    ) -> None:
        normalized_name = name.strip() if isinstance(name, str) else ""
        normalized_category = (
            category.strip() if isinstance(category, str) else ""
        )

        if not normalized_name:
            raise InvalidEvaluationError(
                "Evaluation name must not be empty."
            )

        if not normalized_category:
            raise InvalidEvaluationError(
                "Evaluation category must not be empty."
            )

        if not callable(evaluator):
            raise InvalidEvaluationError(
                "Evaluator must be callable."
            )

        if normalized_name in self._evaluators:
            raise DuplicateEvaluationError(
                f"Evaluation '{normalized_name}' is already registered."
            )

        self._evaluators[normalized_name] = {
            "category": normalized_category,
            "evaluator": evaluator,
        }

    def unregister(self, name: str) -> None:
        if name not in self._evaluators:
            raise EvaluationNotFoundError(
                f"Evaluation '{name}' was not found."
            )

        del self._evaluators[name]

    def get(self, name: str) -> dict[str, Any]:
        if name not in self._evaluators:
            raise EvaluationNotFoundError(
                f"Evaluation '{name}' was not found."
            )

        return self._evaluators[name].copy()

    def list_evaluations(self) -> list[dict[str, str]]:
        return [
            {
                "name": name,
                "category": definition["category"],
            }
            for name, definition in self._evaluators.items()
        ]

    def get_evaluator_names(self) -> list[str]:
        return list(self._evaluators.keys())

    def clear(self) -> None:
        self._evaluators.clear()

    def __len__(self) -> int:
        return len(self._evaluators)
