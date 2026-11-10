"""Instance-scoped evaluator registry; no process-global mutable singleton."""

from threading import RLock

from app.evaluation.core.exceptions import (
    DuplicateEvaluatorError,
    UnknownEvaluatorError,
)


class EvaluationRegistry:

    def __init__(self) -> None:

        self._evaluators = {}

        self._lock = RLock()

    def register(self, evaluator) -> None:

        identifier = getattr(
            evaluator,
            "evaluator_id",
            None
        )

        if (
            not isinstance(identifier, str)
            or not identifier.strip()
        ):
            raise ValueError(
                "Evaluator must expose a non-empty evaluator_id."
            )

        if not callable(
            getattr(evaluator, "evaluate", None)
        ):
            raise TypeError(
                "Evaluator must expose an evaluate method."
            )

        with self._lock:

            if identifier in self._evaluators:

                raise DuplicateEvaluatorError(
                    f"Evaluator already registered: {identifier}"
                )

            self._evaluators[identifier] = evaluator

    def unregister(self, evaluator_id: str) -> None:

        with self._lock:

            if evaluator_id not in self._evaluators:

                raise UnknownEvaluatorError(
                    f"Unknown evaluator: {evaluator_id}"
                )

            del self._evaluators[evaluator_id]

    def get(self, evaluator_id: str):

        with self._lock:

            try:

                return self._evaluators[evaluator_id]

            except KeyError as exc:

                raise UnknownEvaluatorError(
                    f"Unknown evaluator: {evaluator_id}"
                ) from exc

    def exists(self, evaluator_id: str) -> bool:

        with self._lock:

            return evaluator_id in self._evaluators

    def get_all(self) -> tuple:

        with self._lock:

            return tuple(
                self._evaluators.values()
            )

    def get_by_type(self, evaluator_type) -> tuple:

        expected = getattr(
            evaluator_type,
            "value",
            evaluator_type
        )

        with self._lock:

            return tuple(

                item
                for item in self._evaluators.values()

                if getattr(
                    getattr(
                        item,
                        "evaluator_type",
                        None
                    ),
                    "value",
                    getattr(
                        item,
                        "evaluator_type",
                        None
                    )
                ) == expected

            )