from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OptimizationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class OptimizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    optimization_id: str = Field(min_length=1)
    baseline_candidate: OptimizationCandidate
    candidates: list[OptimizationCandidate] = Field(min_length=1)

    objective_metric: str = Field(min_length=1)
    higher_is_better: bool = True

    minimum_improvement: float = Field(default=0.0, ge=0)
    minimum_samples: int = Field(default=1, ge=1)

    guardrail_limits: dict[str, float] = Field(default_factory=dict)
    guardrails_higher_is_better: dict[str, bool] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def validate_candidates(self):
        candidate_ids = [
            candidate.candidate_id for candidate in self.candidates
        ]

        if self.baseline_candidate.candidate_id in candidate_ids:
            raise ValueError(
                "Candidate IDs must not include the baseline candidate."
            )

        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Candidate IDs must be unique.")

        for metric in self.guardrails_higher_is_better:
            if metric not in self.guardrail_limits:
                raise ValueError(
                    f"Guardrail direction configured without a limit: {metric}"
                )

        return self


class CandidateEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)

    metric_values: dict[str, list[float]] = Field(default_factory=dict)
    metric_means: dict[str, float] = Field(default_factory=dict)
    metric_standard_deviations: dict[str, float] = Field(
        default_factory=dict
    )

    sample_counts: dict[str, int] = Field(default_factory=dict)

    objective_score: float | None = None

    eligible: bool = False
    accepted: bool = False

    violations: list[str] = Field(default_factory=list)


class OptimizationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    optimization_id: str

    baseline: CandidateEvaluation
    evaluations: list[CandidateEvaluation]

    selected_candidate_id: str | None = None
    selected_parameters: dict[str, Any] | None = None

    baseline_score: float
    selected_score: float | None = None
    improvement: float | None = None

    completed: bool = False
    passed: bool = False

    summary: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
