class WorkflowError(Exception):
    """Base exception for AI workflow operations."""


class WorkflowRegistrationError(WorkflowError):
    """Invalid workflow registration."""


class WorkflowNotFoundError(WorkflowError):
    """Requested workflow does not exist."""


class WorkflowInputValidationError(WorkflowError):
    """Workflow input failed validation."""


class WorkflowExecutionError(WorkflowError):
    """Workflow execution infrastructure failed."""


class WorkflowStateTransitionError(WorkflowError):
    """Invalid workflow state transition."""


class WorkflowReferenceResolutionError(WorkflowError):
    """A workflow input/output reference cannot be resolved."""