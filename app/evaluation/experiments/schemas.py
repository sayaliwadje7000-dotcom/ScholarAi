from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExperimentObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str = Field(min_length=1)
    variant: str = Field(min_length=1)
    metric_name: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    value: float
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str = Field(min_length=1)
    baseline_variant: str = Field(min_length=1)
    candidate_variant: str = Field(min_length=1)
    metric_name: str = Field(min_length=1)

    higher_is_better: bool = True
    alpha: float = Field(default=0.05, gt=0, lt=1)

    minimum_samples_per_variant: int = Field(default=10, ge=2)
    bootstrap_iterations: int = Field(default=5000, ge=100)
    random_seed: int = 42

    minimum_effect_size: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def validate_variants(self):
        if self.baseline_variant == self.candidate_variant:
            raise ValueError(
                "Baseline and candidate variants must be different."
            )
        return self


class VariantStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: str
    sample_count: int

    mean: float
    median: float
    standard_deviation: float
    standard_error: float

    minimum: float
    maximum: float


class ExperimentComparisonReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    metric_name: str

    baseline_variant: str
    candidate_variant: str

    baseline_statistics: VariantStatistics
    candidate_statistics: VariantStatistics

    paired_sample_count: int

    mean_difference: float
    confidence_interval_lower: float
    confidence_interval_upper: float

    p_value: float
    alpha: float

    effect_size: float
    statistically_significant: bool
    practical_significance: bool

    winner: str | None
    passed: bool

    higher_is_better: bool
    bootstrap_iterations: int

    violations: list[str] = Field(default_factory=list)

    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @model_validator(mode="after")
    def validate_report(self):
        if self.confidence_interval_lower > self.confidence_interval_upper:
            raise ValueError(
                "Confidence interval lower bound cannot exceed upper bound."
            )

        if self.paired_sample_count < 0:
            raise ValueError("Paired sample count cannot be negative.")

        if not 0 <= self.p_value <= 1:
            raise ValueError("p_value must be between 0 and 1.")

        return self


class ExperimentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    config: ExperimentConfig

    observations: list[ExperimentObservation] = Field(
        default_factory=list
    )

    status: str = "created"

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_experiment_id(self):
        if self.experiment_id != self.config.experiment_id:
            raise ValueError(
                "Experiment record ID must match configuration ID."
            )
        return self
