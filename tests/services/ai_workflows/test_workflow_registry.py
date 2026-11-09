import pytest

from pydantic import BaseModel

from app.schemas.ai_workflows import (
    WorkflowFailurePolicy,
)

from app.services.ai_workflows.exceptions import (
    WorkflowRegistrationError,
)

from app.services.ai_workflows.workflow_registry import (
    WorkflowDefinition,
    WorkflowRegistry,
    WorkflowStepDefinition,
)


class InputModel(BaseModel):
    query: str


class OutputModel(BaseModel):
    result: str


def make_step(
    step_id="search",
    dependencies=(),
):

    return WorkflowStepDefinition(
        step_id=step_id,
        tool_name="academic_search",
        arguments_template={
            "query": {
                "$ref": "input.query"
            }
        },
        output_model=OutputModel,
        depends_on=dependencies,
    )


def make_workflow(steps=None):

    return WorkflowDefinition(
        name="study_workflow",
        description="Academic study workflow.",
        input_model=InputModel,
        steps=tuple(
            steps or [make_step()]
        ),
        failure_policy=WorkflowFailurePolicy.STOP,
    )


def test_registers_workflow():

    registry = WorkflowRegistry()

    definition = make_workflow()

    registry.register(definition)

    assert registry.get(
        "study_workflow"
    ) is definition


def test_rejects_duplicate_workflow():

    registry = WorkflowRegistry()

    definition = make_workflow()

    registry.register(definition)

    with pytest.raises(WorkflowRegistrationError):

        registry.register(definition)


def test_rejects_duplicate_step_ids():

    registry = WorkflowRegistry()

    definition = make_workflow(
        [
            make_step("search"),
            make_step("search"),
        ]
    )

    with pytest.raises(WorkflowRegistrationError):

        registry.register(definition)


def test_rejects_unknown_dependency():

    registry = WorkflowRegistry()

    definition = make_workflow(
        [
            make_step(
                "search",
                ("unknown_step",),
            )
        ]
    )

    with pytest.raises(WorkflowRegistrationError):

        registry.register(definition)


def test_rejects_dependency_cycle():

    registry = WorkflowRegistry()

    definition = make_workflow(
        [
            make_step("search", ("summary",)),
            make_step("summary", ("search",)),
        ]
    )

    with pytest.raises(WorkflowRegistrationError):

        registry.register(definition)


def test_rejects_invalid_final_output_step():

    registry = WorkflowRegistry()

    definition = WorkflowDefinition(
        name="study_workflow",
        description="Study workflow.",
        input_model=InputModel,
        steps=(make_step(),),
        final_output_step="missing_step",
    )

    with pytest.raises(WorkflowRegistrationError):

        registry.register(definition)