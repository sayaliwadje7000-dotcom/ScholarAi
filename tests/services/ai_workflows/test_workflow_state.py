import pytest

from app.schemas.ai_workflows import (
    WorkflowStatus,
    WorkflowStepStatus,
)

from app.services.ai_workflows.exceptions import (
    WorkflowStateTransitionError,
)

from app.services.ai_workflows.workflow_state import (
    WorkflowStateMachine,
)


def test_workflow_pending_to_running():

    result = WorkflowStateMachine.transition_workflow(
        WorkflowStatus.PENDING,
        WorkflowStatus.RUNNING,
    )

    assert result == WorkflowStatus.RUNNING


def test_workflow_running_to_succeeded():

    result = WorkflowStateMachine.transition_workflow(
        WorkflowStatus.RUNNING,
        WorkflowStatus.SUCCEEDED,
    )

    assert result == WorkflowStatus.SUCCEEDED


def test_rejects_invalid_workflow_transition():

    with pytest.raises(WorkflowStateTransitionError):

        WorkflowStateMachine.transition_workflow(
            WorkflowStatus.SUCCEEDED,
            WorkflowStatus.RUNNING,
        )


def test_step_pending_to_running():

    result = WorkflowStateMachine.transition_step(
        WorkflowStepStatus.PENDING,
        WorkflowStepStatus.RUNNING,
    )

    assert result == WorkflowStepStatus.RUNNING


def test_step_running_to_failed():

    result = WorkflowStateMachine.transition_step(
        WorkflowStepStatus.RUNNING,
        WorkflowStepStatus.FAILED,
    )

    assert result == WorkflowStepStatus.FAILED


def test_rejects_invalid_step_transition():

    with pytest.raises(WorkflowStateTransitionError):

        WorkflowStateMachine.transition_step(
            WorkflowStepStatus.SUCCEEDED,
            WorkflowStepStatus.RUNNING,
        )