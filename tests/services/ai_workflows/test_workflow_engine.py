import pytest

from pydantic import BaseModel, ConfigDict, Field

from app.core.llm_tool_config import (
    LLMToolSettings,
)

from app.schemas.ai_workflows import (
    WorkflowFailurePolicy,
    WorkflowStatus,
    WorkflowStepStatus,
)

from app.schemas.llm_tools import (
    ToolExecutionContext,
    ToolExecutionStatus,
)
from app.services.ai_workflows.exceptions import (
    WorkflowInputValidationError,
    WorkflowNotFoundError,
)

from app.services.ai_workflows.workflow_registry import (
    WorkflowDefinition,
    WorkflowRegistry,
    WorkflowStepDefinition,
)

from app.services.ai_workflows.workflow_engine import (
    WorkflowExecutionEngine,
)

from app.services.llm_tools.tool_registry import (
    ToolDefinition,
    ToolRegistry,
)

from app.services.llm_tools.tool_executor import (
    ToolExecutionService,
)


class WorkflowInputs(BaseModel):

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=3,
        max_length=100,
    )


class SearchArguments(BaseModel):

    model_config = ConfigDict(extra="forbid")

    query: str


class SearchOutput(BaseModel):

    model_config = ConfigDict(extra="forbid")

    query: str

    count: int


class SummaryArguments(BaseModel):

    model_config = ConfigDict(extra="forbid")

    query: str

    count: int


class SummaryOutput(BaseModel):

    model_config = ConfigDict(extra="forbid")

    summary: str


@pytest.fixture
def context():

    return ToolExecutionContext(
        request_id="workflow-test-001",
    )


@pytest.fixture
def setup_engine():

    tool_registry = ToolRegistry()

    workflow_registry = WorkflowRegistry()

    async def search_handler(arguments, context):

        return {
            "query": arguments.query,
            "count": 3,
        }

    async def summary_handler(arguments, context):

        return {
            "summary": (
                f"Summary for {arguments.query}; "
                f"resources found: {arguments.count}"
            )
        }

    tool_registry.register(
        ToolDefinition(
            name="academic_search",
            description="Search academic resources.",
            arguments_model=SearchArguments,
            handler=search_handler,
        )
    )

    tool_registry.register(
        ToolDefinition(
            name="generate_summary",
            description="Generate a resource summary.",
            arguments_model=SummaryArguments,
            handler=summary_handler,
        )
    )

    tool_settings = LLMToolSettings(
        max_tool_calls_per_request=5,
        tool_execution_timeout_seconds=2,
        max_tool_arguments_bytes=4096,
        max_tool_output_characters=4096,
    )

    executor = ToolExecutionService(
        tool_registry,
        tool_settings,
    )

    definition = WorkflowDefinition(
        name="study_workflow",
        description="Search and summarize academic resources.",
        input_model=WorkflowInputs,
        steps=(
            WorkflowStepDefinition(
                step_id="resource_search",
                tool_name="academic_search",
                arguments_template={
                    "query": {
                        "$ref": "input.query"
                    }
                },
                output_model=SearchOutput,
            ),
            WorkflowStepDefinition(
                step_id="summary",
                tool_name="generate_summary",
                arguments_template={
                    "query": {
                        "$ref": (
                            "steps.resource_search.output.query"
                        )
                    },
                    "count": {
                        "$ref": (
                            "steps.resource_search.output.count"
                        )
                    },
                },
                output_model=SummaryOutput,
                depends_on=("resource_search",),
            ),
        ),
        failure_policy=WorkflowFailurePolicy.STOP,
        final_output_step="summary",
    )

    workflow_registry.register(
        definition
    )

    engine = WorkflowExecutionEngine(
        registry=workflow_registry,
        tool_executor=executor,
    )

    return engine, tool_registry, workflow_registry


@pytest.mark.asyncio
async def test_executes_complete_workflow(
    setup_engine,
    context,
):

    engine, _, _ = setup_engine

    result = await engine.execute(
        workflow_name="study_workflow",
        inputs={
            "query": "binary search",
        },
        context=context,
    )

    assert result.status == WorkflowStatus.SUCCEEDED

    assert len(result.steps) == 2

    assert all(
        step.status == WorkflowStepStatus.SUCCEEDED
        for step in result.steps
    )

    assert result.final_output["summary"].startswith(
        "Summary for binary search"
    )


@pytest.mark.asyncio
async def test_tracks_execution(
    setup_engine,
    context,
):

    engine, _, _ = setup_engine

    result = await engine.execute(
        workflow_name="study_workflow",
        inputs={
            "query": "binary search",
        },
        context=context,
    )

    stored = engine.get_execution(
        result.execution_id
    )

    assert stored is not None

    assert stored.execution_id == result.execution_id


@pytest.mark.asyncio
async def test_rejects_unknown_workflow(
    setup_engine,
    context,
):

    engine, _, _ = setup_engine

    with pytest.raises(WorkflowNotFoundError):

        await engine.execute(
            workflow_name="unknown_workflow",
            inputs={},
            context=context,
        )


@pytest.mark.asyncio
async def test_rejects_invalid_workflow_inputs(
    setup_engine,
    context,
):

    engine, _, _ = setup_engine

    with pytest.raises(WorkflowInputValidationError):

        await engine.execute(
            workflow_name="study_workflow",
            inputs={
                "query": "x",
            },
            context=context,
        )


@pytest.mark.asyncio
async def test_stops_after_failed_step(
    setup_engine,
    context,
):

    engine, tool_registry, workflow_registry = setup_engine

    tool_registry.clear()

    definition = workflow_registry.get(
        "study_workflow"
    )

    async def failing_search(arguments, execution_context):

        raise RuntimeError("Search unavailable")

    tool_registry.register(
        ToolDefinition(
            name="academic_search",
            description="Search academic resources.",
            arguments_model=SearchArguments,
            handler=failing_search,
        )
    )

    result = await engine.execute(
        workflow_name="study_workflow",
        inputs={
            "query": "binary search",
        },
        context=context,
    )

    assert result.status == WorkflowStatus.FAILED

    assert result.steps[0].status == WorkflowStepStatus.FAILED

    assert result.steps[1].status == WorkflowStepStatus.SKIPPED


@pytest.mark.asyncio
async def test_continue_policy_runs_independent_steps(
    context,
):

    tool_registry = ToolRegistry()

    workflow_registry = WorkflowRegistry()

    class EmptyArguments(BaseModel):
        model_config = ConfigDict(extra="forbid")

    class EmptyOutput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        result: str

    async def failing_handler(arguments, execution_context):

        raise RuntimeError("Failure")

    async def successful_handler(arguments, execution_context):

        return {
            "result": "completed"
        }

    tool_registry.register(
        ToolDefinition(
            name="failing_tool",
            description="Failing tool.",
            arguments_model=EmptyArguments,
            handler=failing_handler,
        )
    )

    tool_registry.register(
        ToolDefinition(
            name="successful_tool",
            description="Successful tool.",
            arguments_model=EmptyArguments,
            handler=successful_handler,
        )
    )

    workflow_registry.register(
        WorkflowDefinition(
            name="recovery_workflow",
            description="Workflow testing failure recovery.",
            input_model=EmptyArguments,
            steps=(
                WorkflowStepDefinition(
                    step_id="first",
                    tool_name="failing_tool",
                    arguments_template={},
                    output_model=EmptyOutput,
                ),
                WorkflowStepDefinition(
                    step_id="second",
                    tool_name="successful_tool",
                    arguments_template={},
                    output_model=EmptyOutput,
                ),
            ),
            failure_policy=WorkflowFailurePolicy.CONTINUE,
        )
    )

    settings = LLMToolSettings(
        max_tool_calls_per_request=5,
        tool_execution_timeout_seconds=2,
        max_tool_arguments_bytes=4096,
        max_tool_output_characters=4096,
    )

    executor = ToolExecutionService(
        tool_registry,
        settings,
    )

    engine = WorkflowExecutionEngine(
        workflow_registry,
        executor,
    )

    result = await engine.execute(
        "recovery_workflow",
        {},
        context,
    )

    assert result.status == WorkflowStatus.PARTIALLY_SUCCEEDED

    assert result.steps[0].status == WorkflowStepStatus.FAILED

    assert result.steps[1].status == WorkflowStepStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_rejects_invalid_tool_output(
    context,
):

    tool_registry = ToolRegistry()

    workflow_registry = WorkflowRegistry()

    class EmptyArguments(BaseModel):
        model_config = ConfigDict(extra="forbid")

    class ExpectedOutput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        result: str

    async def invalid_handler(arguments, execution_context):

        return {
            "unexpected": "value"
        }

    tool_registry.register(
        ToolDefinition(
            name="invalid_tool",
            description="Returns invalid output.",
            arguments_model=EmptyArguments,
            handler=invalid_handler,
        )
    )

    workflow_registry.register(
        WorkflowDefinition(
            name="validation_workflow",
            description="Validates tool output.",
            input_model=EmptyArguments,
            steps=(
                WorkflowStepDefinition(
                    step_id="first",
                    tool_name="invalid_tool",
                    arguments_template={},
                    output_model=ExpectedOutput,
                ),
            ),
        )
    )

    executor = ToolExecutionService(
        tool_registry,
        LLMToolSettings(
            max_tool_calls_per_request=5,
            tool_execution_timeout_seconds=2,
            max_tool_arguments_bytes=4096,
            max_tool_output_characters=4096,
        ),
    )

    engine = WorkflowExecutionEngine(
        workflow_registry,
        executor,
    )

    result = await engine.execute(
        "validation_workflow",
        {},
        context,
    )

    assert result.status == WorkflowStatus.FAILED

    assert result.steps[0].status == WorkflowStepStatus.FAILED