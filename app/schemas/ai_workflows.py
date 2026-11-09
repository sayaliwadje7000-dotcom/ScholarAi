from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIALLY_SUCCEEDED = "partially_succeeded"


class WorkflowStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowFailurePolicy(str, Enum):
    STOP = "stop"
    CONTINUE = "continue"


class WorkflowStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str

    tool_name: str

    status: WorkflowStepStatus

    output: Any = None

    error: str | None = None

    execution_time_ms: float = Field(ge=0)


class WorkflowExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_name: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    )

    inputs: dict[str, Any] = Field(
        default_factory=dict,
    )


class WorkflowExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str

    workflow_name: str

    status: WorkflowStatus

    steps: list[WorkflowStepResult]

    final_output: Any = None

    error: str | None = None

    started_at: str

    completed_at: str | None = None

    execution_time_ms: float = Field(ge=0)

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
                    "Workflow error cannot be empty."
                )

        return value