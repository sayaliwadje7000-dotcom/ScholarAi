import re

from dataclasses import dataclass, field
from typing import Any, Type

from pydantic import BaseModel

from app.schemas.ai_workflows import (
    WorkflowFailurePolicy,
)

from app.services.ai_workflows.exceptions import (
    WorkflowRegistrationError,
)


@dataclass(frozen=True)
class WorkflowStepDefinition:

    step_id: str

    tool_name: str

    arguments_template: dict[str, Any]

    output_model: Type[BaseModel]

    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowDefinition:

    name: str

    description: str

    input_model: Type[BaseModel]

    steps: tuple[WorkflowStepDefinition, ...]

    failure_policy: WorkflowFailurePolicy = (
        WorkflowFailurePolicy.STOP
    )

    final_output_step: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class WorkflowRegistry:

    def __init__(self):

        self._workflows: dict[
            str,
            WorkflowDefinition
        ] = {}

    @staticmethod
    def _validate_model(
        model: Type[BaseModel],
        label: str,
    ) -> None:

        if (
            not isinstance(model, type)
            or not issubclass(model, BaseModel)
        ):

            raise WorkflowRegistrationError(
                f"{label} must be a Pydantic model."
            )

    def _validate_definition(
        self,
        definition: WorkflowDefinition,
    ) -> None:

        if not re.fullmatch(
            r"[a-z][a-z0-9_]*",
            definition.name,
        ):

            raise WorkflowRegistrationError(
                "Invalid workflow name."
            )

        if not definition.description.strip():

            raise WorkflowRegistrationError(
                "Workflow description cannot be empty."
            )

        self._validate_model(
            definition.input_model,
            "Workflow input model",
        )

        if not definition.steps:

            raise WorkflowRegistrationError(
                "A workflow must contain at least one step."
            )

        step_ids = [
            step.step_id
            for step in definition.steps
        ]

        if len(step_ids) != len(set(step_ids)):

            raise WorkflowRegistrationError(
                "Workflow step IDs must be unique."
            )

        available_ids = set(step_ids)

        for step in definition.steps:

            if not re.fullmatch(
                r"[a-z][a-z0-9_]*",
                step.step_id,
            ):

                raise WorkflowRegistrationError(
                    "Invalid workflow step ID."
                )

            if not re.fullmatch(
                r"[a-z][a-z0-9_]*",
                step.tool_name,
            ):

                raise WorkflowRegistrationError(
                    "Invalid tool name in workflow step."
                )

            self._validate_model(
                step.output_model,
                f"Output model for {step.step_id}",
            )

            if not isinstance(
                step.arguments_template,
                dict,
            ):

                raise WorkflowRegistrationError(
                    "Step arguments must be a dictionary."
                )

            if step.step_id in step.depends_on:

                raise WorkflowRegistrationError(
                    "A step cannot depend on itself."
                )

            if len(step.depends_on) != len(
                set(step.depends_on)
            ):

                raise WorkflowRegistrationError(
                    "Duplicate step dependencies are not allowed."
                )

            for dependency in step.depends_on:

                if dependency not in available_ids:

                    raise WorkflowRegistrationError(
                        f"Unknown dependency '{dependency}'."
                    )

        if (
            definition.final_output_step is not None
            and definition.final_output_step not in available_ids
        ):

            raise WorkflowRegistrationError(
                "Final output step does not exist."
            )

        self._validate_acyclic_dependencies(
            definition.steps
        )

    @staticmethod
    def _validate_acyclic_dependencies(
        steps: tuple[WorkflowStepDefinition, ...],
    ) -> None:

        dependencies = {
            step.step_id: set(step.depends_on)
            for step in steps
        }

        resolved = set()

        while True:

            ready = {
                step_id
                for step_id, required in dependencies.items()
                if step_id not in resolved
                and required.issubset(resolved)
            }

            if not ready:
                break

            resolved.update(ready)

        if len(resolved) != len(steps):

            raise WorkflowRegistrationError(
                "Workflow contains a dependency cycle."
            )

    def register(
        self,
        definition: WorkflowDefinition,
    ) -> None:

        self._validate_definition(definition)

        if definition.name in self._workflows:

            raise WorkflowRegistrationError(
                f"Workflow '{definition.name}' is already registered."
            )

        self._workflows[definition.name] = definition

    def get(
        self,
        name: str,
    ) -> WorkflowDefinition | None:

        return self._workflows.get(name)

    def list_workflows(self) -> list[WorkflowDefinition]:

        return list(
            self._workflows.values()
        )

    def contains(self, name: str) -> bool:

        return name in self._workflows

    def clear(self) -> None:

        self._workflows.clear()


workflow_registry = WorkflowRegistry()