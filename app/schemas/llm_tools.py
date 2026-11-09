from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ToolExecutionStatus(str, Enum):
    SUCCESS = "success"
    TOOL_NOT_FOUND = "tool_not_found"
    INVALID_ARGUMENTS = "invalid_arguments"
    UNAUTHORIZED = "unauthorized"
    TIMEOUT = "timeout"
    EXECUTION_FAILED = "execution_failed"
    OUTPUT_TOO_LARGE = "output_too_large"


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str = Field(
        min_length=1,
        max_length=128,
    )

    tool_name: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    )

    arguments: dict[str, Any] = Field(
        default_factory=dict,
    )


class ToolExecutionContext(BaseModel):
    """
    Context supplied by trusted application code.

    Do not populate user_id from an LLM-generated argument.
    Authentication integration belongs to Phase 18.
    """

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(
        min_length=1,
        max_length=128,
    )

    conversation_id: str | None = None

    user_id: str | None = None


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str

    tool_name: str

    status: ToolExecutionStatus

    output: Any = None

    error: str | None = None

    execution_time_ms: float = Field(
        ge=0,
    )

    @field_validator("error")
    @classmethod
    def validate_error(
        cls,
        value: str | None,
    ) -> str | None:

        if value is not None:
            value = value.strip()

            if not value:
                raise ValueError(
                    "Error message cannot be empty."
                )

        return value


class ToolDefinitionResponse(BaseModel):
    """
    Public tool metadata.

    Internal Python handlers are never exposed.
    """

    model_config = ConfigDict(extra="forbid")

    name: str

    description: str

    parameters_schema: dict[str, Any]

    requires_authenticated_user: bool

    enabled: bool