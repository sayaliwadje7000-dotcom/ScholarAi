from app.schemas.ai_workflows import (
    WorkflowStatus,
    WorkflowStepStatus,
)

from app.services.ai_workflows.exceptions import (
    WorkflowStateTransitionError,
)


WORKFLOW_TRANSITIONS = {

    WorkflowStatus.PENDING: {
        WorkflowStatus.RUNNING,
        WorkflowStatus.FAILED,
    },

    WorkflowStatus.RUNNING: {
        WorkflowStatus.SUCCEEDED,
        WorkflowStatus.FAILED,
        WorkflowStatus.PARTIALLY_SUCCEEDED,
    },

    WorkflowStatus.SUCCEEDED: set(),

    WorkflowStatus.FAILED: set(),

    WorkflowStatus.PARTIALLY_SUCCEEDED: set(),
}


STEP_TRANSITIONS = {

    WorkflowStepStatus.PENDING: {
        WorkflowStepStatus.RUNNING,
        WorkflowStepStatus.SKIPPED,
    },

    WorkflowStepStatus.RUNNING: {
        WorkflowStepStatus.SUCCEEDED,
        WorkflowStepStatus.FAILED,
    },

    WorkflowStepStatus.SUCCEEDED: set(),

    WorkflowStepStatus.FAILED: set(),

    WorkflowStepStatus.SKIPPED: set(),
}


class WorkflowStateMachine:

    @staticmethod
    def transition_workflow(
        current: WorkflowStatus,
        target: WorkflowStatus,
    ) -> WorkflowStatus:

        allowed = WORKFLOW_TRANSITIONS[current]

        if target not in allowed:

            raise WorkflowStateTransitionError(
                f"Invalid workflow transition: "
                f"{current.value} -> {target.value}"
            )

        return target

    @staticmethod
    def transition_step(
        current: WorkflowStepStatus,
        target: WorkflowStepStatus,
    ) -> WorkflowStepStatus:

        allowed = STEP_TRANSITIONS[current]

        if target not in allowed:

            raise WorkflowStateTransitionError(
                f"Invalid step transition: "
                f"{current.value} -> {target.value}"
            )

        return target