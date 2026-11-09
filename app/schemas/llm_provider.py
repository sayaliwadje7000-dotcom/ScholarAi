from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class LLMProviderStatus(str, Enum):

    SUCCESS = "success"

    FAILED = "failed"

    FALLBACK_SUCCESS = "fallback_success"

    ALL_PROVIDERS_FAILED = "all_providers_failed"


class LLMProviderAttempt(BaseModel):

    model_config = ConfigDict(extra="forbid")

    provider: str

    success: bool

    retryable: bool

    execution_time_ms: float = Field(
        ge=0,
    )

    error_code: str | None = None


class LLMGenerationResult(BaseModel):

    model_config = ConfigDict(extra="forbid")

    response: str

    provider: str

    status: LLMProviderStatus

    attempts: list[LLMProviderAttempt]

    total_execution_time_ms: float = Field(
        ge=0,
    )