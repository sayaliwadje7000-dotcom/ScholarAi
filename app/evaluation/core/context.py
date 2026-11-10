"""Execution-scoped metadata. Contains no student payload by default."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class EvaluationContext:

    execution_id: str
    evaluator_id: str

    started_at: datetime

    dataset_name: str | None = None
    dataset_version: str | None = None

    model_name: str | None = None
    model_version: str | None = None

    prompt_version: str | None = None

    tags: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(cls, config) -> "EvaluationContext":

        return cls(
            execution_id=str(uuid4()),

            evaluator_id=config.evaluator_id,

            started_at=datetime.now(timezone.utc),

            dataset_name=config.dataset_name,
            dataset_version=config.dataset_version,

            model_name=config.model_name,
            model_version=config.model_version,

            prompt_version=config.prompt_version,

            tags=dict(config.tags),
        )