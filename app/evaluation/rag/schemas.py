from dataclasses import dataclass, field
from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.rag_evaluation import RAGEvaluationResult


class RAGBenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    required_terms: list[str] = Field(default_factory=list)
    expected_citation_source_ids: list[str] = Field(default_factory=list)
    answerable: bool = True


class RAGBenchmarkDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_name: str = Field(min_length=1)
    version: str = Field(default="1.0", min_length=1)
    cases: list[RAGBenchmarkCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_case_ids(self):
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Dataset contains duplicate case IDs")
        return self


@dataclass(frozen=True, slots=True)
class RAGBenchmarkConfig:
    k: int = 5
    max_concurrency: int = 5
    timeout_seconds: float = 60.0
    minimum_recall: float = 0.60
    minimum_answer_f1: float = 0.30
    minimum_citation_precision: float = 0.80

    def __post_init__(self) -> None:
        if isinstance(self.k, bool) or not isinstance(self.k, int) or self.k < 1:
            raise ValueError("k must be a positive integer")

        if isinstance(self.max_concurrency, bool) or not isinstance(self.max_concurrency, int) or self.max_concurrency < 1:
            raise ValueError("max_concurrency must be a positive integer")

        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or not isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive finite number")

        thresholds = {
            "minimum_recall": self.minimum_recall,
            "minimum_answer_f1": self.minimum_answer_f1,
            "minimum_citation_precision": self.minimum_citation_precision,
        }

        for name, value in thresholds.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(slots=True)
class RAGBenchmarkCaseOutcome:
    case_id: str
    result: RAGEvaluationResult | None = None
    latency_ms: float = 0.0
    retrieval_metrics: dict[str, float] = field(default_factory=dict)
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.result is not None and self.result.passed

    @property
    def status(self) -> str:
        if self.error is not None:
            return "error"
        return "passed" if self.passed else "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "passed": self.passed,
            "latency_ms": self.latency_ms,
            "retrieval_metrics": self.retrieval_metrics,
            "result": self.result.model_dump(mode="json") if self.result is not None else None,
            "error": self.error,
        }


@dataclass(slots=True)
class RAGBenchmarkReport:
    dataset_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    pass_rate: float
    average_metrics: dict[str, float]
    outcomes: list[RAGBenchmarkCaseOutcome]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "error_cases": self.error_cases,
            "pass_rate": self.pass_rate,
            "average_metrics": self.average_metrics,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }
