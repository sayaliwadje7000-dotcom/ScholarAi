"""Strict state machine for evaluation run lifecycle."""

from enum import Enum

from app.evaluation.core.exceptions import (
    InvalidEvaluationTransitionError
)


class EvaluationStatus(str, Enum):

    PENDING = "pending"

    RUNNING = "running"

    COMPLETED = "completed"

    FAILED = "failed"

    CANCELLED = "cancelled"


_ALLOWED = {

    EvaluationStatus.PENDING: {
        EvaluationStatus.RUNNING,
        EvaluationStatus.CANCELLED,
    },

    EvaluationStatus.RUNNING: {
        EvaluationStatus.COMPLETED,
        EvaluationStatus.FAILED,
        EvaluationStatus.CANCELLED,
    },

    EvaluationStatus.COMPLETED: set(),

    EvaluationStatus.FAILED: set(),

    EvaluationStatus.CANCELLED: set(),
}


class EvaluationLifecycle:

    def __init__(self) -> None:

        self._status = EvaluationStatus.PENDING

        self._history = [
            self._status
        ]

    @property
    def status(self) -> EvaluationStatus:

        return self._status

    @property
    def history(self) -> tuple[EvaluationStatus, ...]:

        return tuple(self._history)

    def transition(self, target: EvaluationStatus) -> None:

        if target not in _ALLOWED[self._status]:

            raise InvalidEvaluationTransitionError(
                f"Cannot transition evaluation from "
                f"{self._status.value} to {target.value}."
            )

        self._status = target

        self._history.append(target)