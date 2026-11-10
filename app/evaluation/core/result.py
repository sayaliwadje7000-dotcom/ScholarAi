"""Stable result envelope independent of domain-specific metric schemas."""

from dataclasses import (
    dataclass,
    field,
    asdict
)

from datetime import datetime

from typing import Any


@dataclass(frozen=True, slots=True)
class EvaluationResult:

    execution_id: str

    evaluator_id: str

    evaluator_type: str

    evaluator_version: str

    status: str

    metrics: dict[str, Any]

    started_at: datetime

    completed_at: datetime

    duration_ms: float

    dataset_name: str | None = None

    dataset_version: str | None = None

    model_name: str | None = None

    model_version: str | None = None

    prompt_version: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    error: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:

        data = asdict(self)

        data["started_at"] = (
            self.started_at.isoformat()
        )

        data["completed_at"] = (
            self.completed_at.isoformat()
        )

        return data