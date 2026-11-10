from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class RecommendationBenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    query: str = Field(min_length=1)

    relevant_item_ids: list[str] = Field(default_factory=list)
    expected_item_ids: list[str] = Field(default_factory=list)

    user_preference_tags: list[str] = Field(default_factory=list)
    item_tags: dict[str, list[str]] = Field(default_factory=dict)
    item_popularity: dict[str, float] = Field(default_factory=dict)
    discovery_item_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self):
        collections = {
            "relevant_item_ids": self.relevant_item_ids,
            "expected_item_ids": self.expected_item_ids,
            "discovery_item_ids": self.discovery_item_ids,
        }

        for name, values in collections.items():
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must not contain duplicate IDs")

        return self


class RecommendationBenchmarkDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_name: str = Field(min_length=1)
    version: str = Field(default="1.0", min_length=1)
    cases: list[RecommendationBenchmarkCase] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_case_ids(self):
        case_ids = [case.case_id for case in self.cases]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Dataset case IDs must be unique")

        return self


class RecommendationEvaluationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    k: int = Field(default=5, ge=1)
    minimum_precision: float = Field(default=0.0, ge=0.0, le=1.0)
    minimum_recall: float = Field(default=0.0, ge=0.0, le=1.0)
    minimum_ndcg: float = Field(default=0.0, ge=0.0, le=1.0)
    minimum_personalization: float = Field(default=0.0, ge=0.0, le=1.0)
    minimum_discovery: float = Field(default=0.0, ge=0.0, le=1.0)
    timeout_seconds: float = Field(default=30.0, gt=0)

    @property
    def minimum_discovery_relevance(self) -> float:
        return self.minimum_discovery


class RecommendationCaseMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    hit_rate_at_k: float = 0.0
    reciprocal_rank: float = 0.0
    ndcg_at_k: float = 0.0
    personalization_alignment: float = 0.0
    discovery_relevance: float = 0.0
    intra_list_diversity: float = 0.0
    novelty: float = 0.0
    serendipity: float = 0.0
    latency_ms: float = 0.0


class RecommendationCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    user_id: str | None = None
    recommended_item_ids: list[str] = Field(default_factory=list)
    metrics: RecommendationCaseMetrics
    passed: bool = True
    failed_checks: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RecommendationEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    dataset_name: str
    dataset_version: str = "1.0"
    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)

    pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    average_metrics: dict[str, float] = Field(default_factory=dict)

    case_results: list[RecommendationCaseResult] = Field(
        default_factory=list,
        validation_alias=AliasChoices("case_results", "results"),
    )

    passed: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def results(self) -> list[RecommendationCaseResult]:
        return self.case_results

    @model_validator(mode="after")
    def validate_report(self):
        if self.passed_cases + self.failed_cases != self.total_cases:
            raise ValueError(
                "passed_cases + failed_cases must equal total_cases"
            )

        calculated_rate = (
            self.passed_cases / self.total_cases
            if self.total_cases > 0
            else 0.0
        )

        if self.pass_rate is None:
            self.pass_rate = calculated_rate

        if self.pass_rate != calculated_rate:
            raise ValueError(
                "pass_rate must equal passed_cases / total_cases"
            )

        return self

