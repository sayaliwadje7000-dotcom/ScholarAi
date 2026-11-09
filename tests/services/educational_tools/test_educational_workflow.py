from datetime import datetime, timezone

from types import SimpleNamespace

import pytest

from app.core.llm_tool_config import (
    LLMToolSettings,
)

from app.schemas.llm_tools import (
    ToolExecutionContext,
)

from app.schemas.ai_workflows import (
    WorkflowStatus,
    WorkflowStepStatus,
)

from app.services.ai_workflows.workflow_registry import (
    WorkflowRegistry,
)

from app.services.ai_workflows.workflow_engine import (
    WorkflowExecutionEngine,
)

from app.services.educational_tools.educational_resource_tool import (
    register_educational_resource_tool,
)

from app.services.educational_tools.educational_workflow import (
    register_educational_resource_workflow,
    execute_educational_resource_workflow,
)

from app.services.llm_tools.tool_registry import (
    ToolRegistry,
)

from app.services.llm_tools.tool_executor import (
    ToolExecutionService,
)


class FakeDiscoveryService:

    async def discover(self, request):

        now = datetime.now(timezone.utc)

        return SimpleNamespace(
            model_dump=lambda mode="python": {
                "query": request.query,
                "total_results": 1,
                "resources": [
                    {
                        "provider": "openalex",
                        "external_id": "paper-001",
                        "title": "Introduction to Binary Search",
                        "canonical_url": (
                            "https://example.com/paper"
                        ),
                        "resource_type": "article",
                        "description": "Academic resource.",
                        "authors": ["Example Author"],
                        "subject": request.subject,
                        "language": request.language,
                        "published_at": None,
                        "retrieved_at": now.isoformat(),
                        "license": None,
                        "access_type": "public",
                        "metadata": {},
                    }
                ],
                "providers_searched": ["openalex"],
                "providers_failed": [],
                "retrieved_at": now.isoformat(),
            }
        )


@pytest.fixture
def context():

    return ToolExecutionContext(
        request_id="educational-workflow-test-001",
    )


@pytest.fixture
def engine():

    tool_registry = ToolRegistry()

    workflow_registry = WorkflowRegistry()

    register_educational_resource_tool(
        FakeDiscoveryService(),
        tool_registry,
    )

    register_educational_resource_workflow(
        workflow_registry
    )

    executor = ToolExecutionService(
        registry=tool_registry,
        settings=LLMToolSettings(
            max_tool_calls_per_request=5,
            tool_execution_timeout_seconds=5,
            max_tool_arguments_bytes=16384,
            max_tool_output_characters=12000,
        ),
    )

    return WorkflowExecutionEngine(
        registry=workflow_registry,
        tool_executor=executor,
    )


@pytest.mark.asyncio
async def test_registers_educational_workflow():

    tool_registry = ToolRegistry()

    workflow_registry = WorkflowRegistry()

    register_educational_resource_tool(
        FakeDiscoveryService(),
        tool_registry,
    )

    register_educational_resource_workflow(
        workflow_registry
    )

    assert workflow_registry.contains(
        "educational_resource_discovery"
    )


@pytest.mark.asyncio
async def test_executes_educational_resource_workflow(
    engine,
    context,
):

    result = await execute_educational_resource_workflow(
        query="binary search",
        context=context,
        subject="Data Structures",
        language="en",
        engine=engine,
    )

    assert result.status == WorkflowStatus.SUCCEEDED

    assert len(result.steps) == 1

    assert result.steps[0].status == (
        WorkflowStepStatus.SUCCEEDED
    )

    assert result.final_output["query"] == "binary search"

    assert result.final_output["total_results"] == 1


@pytest.mark.asyncio
async def test_workflow_rejects_invalid_input(
    engine,
    context,
):

    from app.services.ai_workflows.exceptions import (
        WorkflowInputValidationError,
    )

    with pytest.raises(WorkflowInputValidationError):

        await execute_educational_resource_workflow(
            query="x",
            context=context,
            engine=engine,
        )