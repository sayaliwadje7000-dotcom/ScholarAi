from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any


class EvaluationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class EvaluationDimension(str, Enum):
    CORRECTNESS = "correctness"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    INSTRUCTION_FOLLOWING = "instruction_following"
    CITATION_SUPPORT = "citation_support"


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    prompt: str
    reference_answer: str = ""
    expected_keywords: tuple[str, ...] = ()
    forbidden_keywords: tuple[str, ...] = ()
    expected_citations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.case_id.strip():
            raise ValueError("case_id cannot be empty")
        if not self.prompt.strip():
            raise ValueError("prompt cannot be empty")


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model_name: str = "unknown"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.text, str):
            raise TypeError("Response text must be a string")
        if self.prompt_tokens < 0 or self.completion_tokens < 0:
            raise ValueError("Token counts cannot be negative")


@dataclass(frozen=True)
class LLMEvaluationConfig:
    experiment_name: str = "default"
    timeout_seconds: float = 60.0
    max_concurrency: int = 5
    pass_threshold: float = 0.7
    prompt_cost_per_1k_tokens: float = 0.0
    completion_cost_per_1k_tokens: float = 0.0

    def __post_init__(self):
        numeric_values = (
            self.timeout_seconds,
            self.pass_threshold,
            self.prompt_cost_per_1k_tokens,
            self.completion_cost_per_1k_tokens,
        )
        if not all(isfinite(value) for value in numeric_values):
            raise ValueError("Configuration values must be finite")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if not 0 <= self.pass_threshold <= 1:
            raise ValueError("pass_threshold must be between 0 and 1")
        if self.prompt_cost_per_1k_tokens < 0:
            raise ValueError("Prompt token cost cannot be negative")
        if self.completion_cost_per_1k_tokens < 0:
            raise ValueError("Completion token cost cannot be negative")


@dataclass(frozen=True)
class DimensionScore:
    dimension: EvaluationDimension
    score: float
    explanation: str = ""

    def __post_init__(self):
        if not isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("Dimension score must be between 0 and 1")


@dataclass
class LLMCaseResult:
    case_id: str
    status: EvaluationStatus
    response: str = ""
    scores: list[DimensionScore] = field(default_factory=list)
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def average_quality_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(item.score for item in self.scores) / len(self.scores)
