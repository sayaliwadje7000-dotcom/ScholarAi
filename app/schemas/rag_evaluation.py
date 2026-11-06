from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RAGEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)

    expected_chunk_ids: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    required_terms: list[str] = Field(default_factory=list)
    expected_citation_source_ids: list[str] = Field(
        default_factory=list
    )

    answerable: bool = True


class RAGEvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_name: str = Field(min_length=1)
    version: str = "1.0"
    cases: list[RAGEvaluationCase] = Field(min_length=1)


class RAGEvaluationMetrics(BaseModel):
    precision_at_k: float = Field(ge=0, le=1)
    recall_at_k: float = Field(ge=0, le=1)
    reciprocal_rank: float = Field(ge=0, le=1)
    answer_f1: float = Field(ge=0, le=1)
    required_term_coverage: float = Field(ge=0, le=1)
    citation_precision: float = Field(ge=0, le=1)
    citation_recall: float = Field(ge=0, le=1)

    grounded: bool
    abstention_correct: bool

    latency_ms: float = Field(ge=0)


class RAGEvaluationResult(BaseModel):
    case_id: str
    metrics: RAGEvaluationMetrics
    passed: bool
    failed_checks: list[str] = Field(default_factory=list)


class RAGEvaluationReport(BaseModel):
    dataset_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    average_metrics: dict[str, float]
    results: list[RAGEvaluationResult]
