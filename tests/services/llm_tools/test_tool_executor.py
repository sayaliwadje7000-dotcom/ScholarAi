import asyncio

import pytest

from pydantic import BaseModel, ConfigDict, Field

from app.core.llm_tool_config import (
    LLMToolSettings,
)

from app.schemas.llm_tools import (
    ToolCallRequest,
    ToolExecutionContext,
    ToolExecutionStatus,
)

from app.services.llm_tools.tool_registry import (
    ToolDefinition,
    ToolRegistry,
)

from app.services.llm_tools.tool_executor import (
    ToolExecutionService,
)


class SearchArguments(BaseModel):

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=3,
        max_length=100,
    )


@pytest.fixture
def settings():

    return LLMToolSettings(
        max_tool_calls_per_request=3,
        tool_execution_timeout_seconds=1,
        max_tool_arguments_bytes=1024,
        max_tool_output_characters=1000,
    )


@pytest.fixture
def registry():

    return ToolRegistry()


@pytest.fixture
def context():

    return ToolExecutionContext(
        request_id="test-request-001",
        conversation_id="test-conversation",
    )


def make_call(
    tool_name="academic_search",
    arguments=None,
):

    return ToolCallRequest(
        call_id="call-001",
        tool_name=tool_name,
        arguments=arguments or {
            "query": "binary search",
        },
    )


@pytest.mark.asyncio
async def test_successful_tool_execution(
    registry,
    settings,
    context,
):

    async def handler(arguments, execution_context):

        return {
            "query": arguments.query,
            "found": True,
        }

    registry.register(
        ToolDefinition(
            name="academic_search",
            description="Search academic resources.",
            arguments_model=SearchArguments,
            handler=handler,
        )
    )

    service = ToolExecutionService(
        registry,
        settings,
    )

    result = await service.execute(
        make_call(),
        context,
    )

    assert result.status == ToolExecutionStatus.SUCCESS

    assert result.output["query"] == "binary search"


@pytest.mark.asyncio
async def test_rejects_unregistered_tool(
    registry,
    settings,
    context,
):

    service = ToolExecutionService(
        registry,
        settings,
    )

    result = await service.execute(
        make_call("unknown_tool"),
        context,
    )

    assert result.status == ToolExecutionStatus.TOOL_NOT_FOUND


@pytest.mark.asyncio
async def test_rejects_invalid_arguments(
    registry,
    settings,
    context,
):

    async def handler(arguments, execution_context):
        return {}

    registry.register(
        ToolDefinition(
            name="academic_search",
            description="Search academic resources.",
            arguments_model=SearchArguments,
            handler=handler,
        )
    )

    service = ToolExecutionService(
        registry,
        settings,
    )

    result = await service.execute(
        make_call(
            arguments={
                "query": "x",
                "unexpected": "value",
            }
        ),
        context,
    )

    assert result.status == ToolExecutionStatus.INVALID_ARGUMENTS


@pytest.mark.asyncio
async def test_rejects_oversized_arguments(
    registry,
    settings,
    context,
):

    async def handler(arguments, execution_context):
        return {}

    registry.register(
        ToolDefinition(
            name="academic_search",
            description="Search academic resources.",
            arguments_model=SearchArguments,
            handler=handler,
        )
    )

    service = ToolExecutionService(
        registry,
        settings,
    )

    result = await service.execute(
        make_call(
            arguments={
                "query": "A" * 2000,
            }
        ),
        context,
    )

    assert result.status == ToolExecutionStatus.INVALID_ARGUMENTS


@pytest.mark.asyncio
async def test_requires_authenticated_user(
    registry,
    settings,
    context,
):

    async def handler(arguments, execution_context):
        return {}

    registry.register(
        ToolDefinition(
            name="academic_search",
            description="Protected academic search.",
            arguments_model=SearchArguments,
            handler=handler,
            requires_authenticated_user=True,
        )
    )

    service = ToolExecutionService(
        registry,
        settings,
    )

    result = await service.execute(
        make_call(),
        context,
    )

    assert result.status == ToolExecutionStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_tool_timeout(
    registry,
    settings,
    context,
):

    async def slow_handler(arguments, execution_context):

        await asyncio.sleep(2)

        return {}

    registry.register(
        ToolDefinition(
            name="academic_search",
            description="Slow search.",
            arguments_model=SearchArguments,
            handler=slow_handler,
        )
    )

    service = ToolExecutionService(
        registry,
        settings,
    )

    result = await service.execute(
        make_call(),
        context,
    )

    assert result.status == ToolExecutionStatus.TIMEOUT


@pytest.mark.asyncio
async def test_handles_handler_failure(
    registry,
    settings,
    context,
):

    async def failing_handler(arguments, execution_context):

        raise RuntimeError("Internal database details")

    registry.register(
        ToolDefinition(
            name="academic_search",
            description="Failing search.",
            arguments_model=SearchArguments,
            handler=failing_handler,
        )
    )

    service = ToolExecutionService(
        registry,
        settings,
    )

    result = await service.execute(
        make_call(),
        context,
    )

    assert result.status == ToolExecutionStatus.EXECUTION_FAILED

    assert "Internal database details" not in result.error


@pytest.mark.asyncio
async def test_rejects_oversized_output(
    registry,
    settings,
    context,
):

    async def large_handler(arguments, execution_context):

        return {
            "data": "A" * 2000,
        }

    registry.register(
        ToolDefinition(
            name="academic_search",
            description="Large output search.",
            arguments_model=SearchArguments,
            handler=large_handler,
        )
    )

    service = ToolExecutionService(
        registry,
        settings,
    )

    result = await service.execute(
        make_call(),
        context,
    )

    assert result.status == ToolExecutionStatus.OUTPUT_TOO_LARGE


@pytest.mark.asyncio
async def test_executes_multiple_tools_sequentially(
    registry,
    settings,
    context,
):

    execution_order = []

    async def handler(arguments, execution_context):

        execution_order.append(arguments.query)

        return {
            "query": arguments.query,
        }

    registry.register(
        ToolDefinition(
            name="academic_search",
            description="Academic search.",
            arguments_model=SearchArguments,
            handler=handler,
        )
    )

    service = ToolExecutionService(
        registry,
        settings,
    )

    calls = [
        make_call(
            arguments={"query": "binary search"},
        ),
        make_call(
            arguments={"query": "linked lists"},
        ),
    ]

    results = await service.execute_many(
        calls,
        context,
    )

    assert len(results) == 2

    assert all(
        result.status == ToolExecutionStatus.SUCCESS
        for result in results
    )

    assert execution_order == [
        "binary search",
        "linked lists",
    ]


@pytest.mark.asyncio
async def test_enforces_maximum_tool_calls(
    registry,
    settings,
    context,
):

    service = ToolExecutionService(
        registry,
        settings,
    )

    calls = [
        make_call(),
        make_call(),
        make_call(),
        make_call(),
    ]

    results = await service.execute_many(
        calls,
        context,
    )

    assert len(results) == 4

    assert all(
        result.status == ToolExecutionStatus.INVALID_ARGUMENTS
        for result in results
    )