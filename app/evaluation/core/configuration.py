"""Immutable, validated configuration for a single evaluation run."""

from dataclasses import dataclass, field
from typing import Any, Mapping
import math


@dataclass(frozen=True, slots=True)
class EvaluationConfig:

    evaluator_id: str

    dataset_name: str | None = None
    dataset_version: str | None = None

    model_name: str | None = None
    model_version: str | None = None

    prompt_version: str | None = None

    timeout_seconds: float = 120.0
    max_retries: int = 0

    parameters: Mapping[str, Any] = field(default_factory=dict)
    tags: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:

        if not self.evaluator_id or not self.evaluator_id.strip():
            raise ValueError(
                "evaluator_id must be a non-empty string."
            )

        if (
            isinstance(self.timeout_seconds, bool)
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError(
                "timeout_seconds must be finite and greater than zero."
            )

        if (
            isinstance(self.max_retries, bool)
            or not isinstance(self.max_retries, int)
            or self.max_retries < 0
        ):
            raise ValueError(
                "max_retries must be a non-negative integer."
            )

        if any(
            not isinstance(k, str) or not k.strip()
            for k in self.tags
        ):
            raise ValueError(
                "Tag keys must be non-empty strings."
            )

        if any(
            not isinstance(v, str) or not v.strip()
            for v in self.tags.values()
        ):
            raise ValueError(
                "Tag values must be non-empty strings."
            )

        object.__setattr__(
            self,
            "parameters",
            dict(self.parameters)
        )

        object.__setattr__(
            self,
            "tags",
            dict(self.tags)
        )

    def to_dict(self) -> dict[str, Any]:

        return {
            "evaluator_id": self.evaluator_id,

            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,

            "model_name": self.model_name,
            "model_version": self.model_version,

            "prompt_version": self.prompt_version,

            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,

            "parameters": dict(self.parameters),
            "tags": dict(self.tags),
        }