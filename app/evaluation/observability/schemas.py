from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelPricing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(min_length=1)
    input_cost_per_1k_tokens: float = Field(ge=0)
    output_cost_per_1k_tokens: float = Field(ge=0)


class PerformanceSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: str = Field(min_length=1)
    component: str = Field(min_length=1)
    operation: str = Field(min_length=1)

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    latency_ms: float = Field(ge=0)

    success: bool = True

    model_name: str | None = None

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    estimated_cost_usd: float | None = Field(default=None, ge=0)

    metadata: dict[str, Any] = Field(default_factory=dict)


class PerformanceEvaluationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maximum_latency_ms: float | None = Field(default=None, gt=0)
    maximum_p95_latency_ms: float | None = Field(default=None, gt=0)
    maximum_error_rate: float = Field(default=1.0, ge=0, le=1)
    maximum_cost_per_request_usd: float | None = Field(
        default=None,
        ge=0,
    )

    minimum_requests: int = Field(default=1, ge=1)


class PerformanceEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_requests: int = Field(ge=0)
    successful_requests: int = Field(ge=0)
    failed_requests: int = Field(ge=0)

    average_latency_ms: float = Field(ge=0)
    p50_latency_ms: float = Field(ge=0)
    p95_latency_ms: float = Field(ge=0)
    p99_latency_ms: float = Field(ge=0)
    maximum_latency_ms: float = Field(ge=0)

    throughput_requests_per_second: float = Field(ge=0)

    total_input_tokens: int = Field(ge=0)
    total_output_tokens: int = Field(ge=0)

    total_estimated_cost_usd: float = Field(ge=0)
    average_cost_per_request_usd: float = Field(ge=0)

    error_rate: float = Field(ge=0, le=1)

    passed: bool = True
    violations: list[str] = Field(default_factory=list)

    samples: list[PerformanceSample] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_request_counts(self):
        if (
            self.successful_requests + self.failed_requests
            != self.total_requests
        ):
            raise ValueError(
                "Successful and failed requests must equal total requests"
            )

        return self
