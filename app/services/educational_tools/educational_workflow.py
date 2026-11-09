import logging

from app.schemas.ai_workflows import (
    WorkflowFailurePolicy,
)

from app.schemas.educational_tool_schemas import (
    EducationalResourceWorkflowInput,
    EducationalResourceToolOutput,
)

from app.schemas.llm_tools import (
    ToolExecutionContext,
)

from app.services.ai_workflows.workflow_registry import (
    WorkflowDefinition,
    WorkflowRegistry,
    WorkflowStepDefinition,
    workflow_registry,
)

from app.services.ai_workflows.workflow_engine import (
    WorkflowExecutionEngine,
    workflow_execution_engine,
)

from app.services.educational_tools.educational_resource_tool import (
    EDUCATIONAL_RESOURCE_TOOL_NAME,
)


logger = logging.getLogger(__name__)


EDUCATIONAL_RESOURCE_WORKFLOW_NAME = (
    "educational_resource_discovery"
)


def register_educational_resource_workflow(
    registry: WorkflowRegistry = workflow_registry,
) -> None:
    """
    Registers the educational resource discovery workflow.

    The referenced tool must already be registered in the
    Phase 17.5 tool registry.
    """

    if registry.contains(
        EDUCATIONAL_RESOURCE_WORKFLOW_NAME
    ):

        raise ValueError(
            "Educational resource workflow is already registered."
        )

    definition = WorkflowDefinition(
        name=EDUCATIONAL_RESOURCE_WORKFLOW_NAME,
        description=(
            "Discover relevant educational resources using "
            "ScholarAI's configured academic resource providers."
        ),
        input_model=EducationalResourceWorkflowInput,
        steps=(
            WorkflowStepDefinition(
                step_id="educational_resource_search",
                tool_name=EDUCATIONAL_RESOURCE_TOOL_NAME,
                arguments_template={
                    "query": {
                        "$ref": "input.query"
                    },
                    "providers": {
                        "$ref": "input.providers"
                    },
                    "resource_types": {
                        "$ref": "input.resource_types"
                    },
                    "subject": {
                        "$ref": "input.subject"
                    },
                    "language": {
                        "$ref": "input.language"
                    },
                    "limit_per_provider": {
                        "$ref": "input.limit_per_provider"
                    },
                },
                output_model=EducationalResourceToolOutput,
                depends_on=(),
            ),
        ),
        failure_policy=WorkflowFailurePolicy.STOP,
        final_output_step="educational_resource_search",
        metadata={
            "category": "educational_resource_discovery",
            "version": "1.0",
        },
    )

    registry.register(
        definition
    )

    logger.info(
        "Registered educational workflow: %s",
        EDUCATIONAL_RESOURCE_WORKFLOW_NAME,
    )


async def execute_educational_resource_workflow(
    query: str,
    context: ToolExecutionContext,
    providers: list[str] | None = None,
    resource_types: list | None = None,
    subject: str | None = None,
    language: str | None = None,
    limit_per_provider: int = 10,
    engine: WorkflowExecutionEngine = (
        workflow_execution_engine
    ),
):
    """
    Executes the registered educational resource workflow.
    """

    inputs = {
        "query": query,
        "providers": providers,
        "resource_types": resource_types or [],
        "subject": subject,
        "language": language,
        "limit_per_provider": limit_per_provider,
    }

    logger.info(
        "Starting educational resource workflow: "
        "request_id=%s",
        context.request_id,
    )

    return await engine.execute(
        workflow_name=EDUCATIONAL_RESOURCE_WORKFLOW_NAME,
        inputs=inputs,
        context=context,
    )