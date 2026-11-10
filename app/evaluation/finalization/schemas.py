from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FinalEvaluationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    NOT_RUN = "not_run"


class EvaluationCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_name: str = Field(min_length=1, max_length=150)
    category: str = Field(min_length=1, max_length=100)

    status: FinalEvaluationStatus

    message: str = ""
    duration_seconds: float = Field(default=0.0, ge=0.0)

    metrics: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)

    started_at: datetime | None = None
    completed_at: datetime | None = None


class FinalEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(min_length=1)
    status: FinalEvaluationStatus

    total_checks: int = Field(ge=0)
    passed_checks: int = Field(ge=0)
    failed_checks: int = Field(ge=0)
    partial_checks: int = Field(ge=0)
    not_run_checks: int = Field(ge=0)

    success_rate: float = Field(ge=0.0, le=100.0)

    results: list[EvaluationCheckResult] = Field(default_factory=list)

    summary: str = ""
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict[str, Any] = Field(default_factory=dict)
