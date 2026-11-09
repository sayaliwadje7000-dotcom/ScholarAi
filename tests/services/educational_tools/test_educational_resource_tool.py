from datetime import datetime, timezone

from types import SimpleNamespace

import pytest

from app.schemas.educational_resource_discovery import (
    ResourceDiscoveryRequest,
)

from app.schemas.llm_tools import (
    ToolCallRequest,
    ToolExecutionContext,
    ToolExecutionStatus,
)

from app.services.educational_tools.educational_resource_tool import (
    EDUCATIONAL_RESOURCE_TOOL_NAME,
    register_educational_resource_tool,
)

from app.services.llm_tools.tool_registry import (
    ToolRegistry,
)

from app.services.llm_tools.tool_executor import (
    ToolExecutionService,
)

from app.core.llm_tool_config import (
    LLMToolSettings,
)


@pytest.fixture
def context():

    return ToolExecutionContext(
        request_id="educational-tool-test-001",
    )


@pytest.fixture
def settings():

    return LLMToolSettings(
        max_tool_calls_per_request=5,
        tool_execution_timeout_seconds=5,
        max_tool_arguments_bytes=16384,
        max_tool_output_characters=12000,
    )


def make_discovery_response(request):

    return SimpleNamespace(
        query=request.query,
        total_results=1,
        resources=[
            SimpleNamespace(
                provider="youtube",
                external_id="video-001",
                title="Binary Search Explained",
                canonical_url="https://example.com/video",
                resource_type="video",
                description="A binary search explanation.",
                authors=[],
                subject="Data Structures",
                language="en",
                published_at=None,
                retrieved_at=datetime.now(timezone.utc),
                license=None,
                access_type="public",
                metadata={},
            )
        ],
        providers_searched=["youtube"],
        providers_failed=[],
        retrieved_at=datetime.now(timezone.utc),
    )


class FakeDiscoveryService:

    def __init__(self):

        self.received_request = None

    async def discover(self, request):

        assert isinstance(
            request,
            ResourceDiscoveryRequest,
        )

        self.received_request = request

        response = make_discovery_response(
            request
        )

        # Return an object with the same serialization
        # interface as the actual Pydantic response.
        return SimpleNamespace(
            model_dump=lambda mode="python": {
                "query": response.query,
                "total_results": response.total_results,
                "resources": [
                    {
                        "provider": "youtube",
                        "external_id": "video-001",
                        "title": "Binary Search Explained",
                        "canonical_url": (
                            "https://example.com/video"
                        ),
                        "resource_type": "video",
                        "description": (
                            "A binary search explanation."
                        ),
                        "authors": [],
                        "subject": "Data Structures",
                        "language": "en",
                        "published_at": None,
                        "retrieved_at": (
                            response.retrieved_at.isoformat()
                        ),
                        "license": None,
                        "access_type": "public",
                        "metadata": {},
                    }
                ],
                "providers_searched": ["youtube"],
                "providers_failed": [],
                "retrieved_at": (
                    response.retrieved_at.isoformat()
                ),
            }
        )


@pytest.mark.asyncio
async def test_registers_educational_resource_tool():

    registry = ToolRegistry()

    discovery_service = FakeDiscoveryService()

    register_educational_resource_tool(
        discovery_service,
        registry,
    )

    assert registry.get(
        EDUCATIONAL_RESOURCE_TOOL_NAME
    ) is not None


@pytest.mark.asyncio
async def test_executes_educational_resource_search(
    context,
    settings,
):

    registry = ToolRegistry()

    discovery_service = FakeDiscoveryService()

    register_educational_resource_tool(
        discovery_service,
        registry,
    )

    executor = ToolExecutionService(
        registry,
        settings,
    )

    call = ToolCallRequest(
        call_id="call-001",
        tool_name=EDUCATIONAL_RESOURCE_TOOL_NAME,
        arguments={
            "query": "binary search",
            "subject": "Data Structures",
            "language": "en",
            "limit_per_provider": 5,
        },
    )

    result = await executor.execute(
        call,
        context,
    )

    assert result.status == ToolExecutionStatus.SUCCESS

    assert result.output["query"] == "binary search"

    assert result.output["total_results"] == 1

    assert result.output["resources"][0]["title"] == (
        "Binary Search Explained"
    )

    assert discovery_service.received_request is not None

    assert discovery_service.received_request.query == (
        "binary search"
    )


@pytest.mark.asyncio
async def test_rejects_invalid_search_arguments(
    context,
    settings,
):

    registry = ToolRegistry()

    register_educational_resource_tool(
        FakeDiscoveryService(),
        registry,
    )

    executor = ToolExecutionService(
        registry,
        settings,
    )

    call = ToolCallRequest(
        call_id="call-002",
        tool_name=EDUCATIONAL_RESOURCE_TOOL_NAME,
        arguments={
            "query": "x",
            "unexpected": "value",
        },
    )

    result = await executor.execute(
        call,
        context,
    )

    assert result.status == ToolExecutionStatus.INVALID_ARGUMENTS


@pytest.mark.asyncio
async def test_rejects_duplicate_registration():

    registry = ToolRegistry()

    discovery_service = FakeDiscoveryService()

    register_educational_resource_tool(
        discovery_service,
        registry,
    )

    with pytest.raises(ValueError):

        register_educational_resource_tool(
            discovery_service,
            registry,
        )