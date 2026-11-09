import pytest

from pydantic import BaseModel, ConfigDict

from app.services.llm_tools.exceptions import (
    ToolRegistrationError,
)

from app.services.llm_tools.tool_registry import (
    ToolDefinition,
    ToolRegistry,
)


class ExampleArguments(BaseModel):

    model_config = ConfigDict(extra="forbid")

    query: str


async def example_handler(arguments, context):

    return {
        "query": arguments.query,
    }


def test_registers_tool():

    registry = ToolRegistry()

    definition = ToolDefinition(
        name="example_search",
        description="Example search tool.",
        arguments_model=ExampleArguments,
        handler=example_handler,
    )

    registry.register(definition)

    assert registry.get("example_search") is definition


def test_rejects_duplicate_tool():

    registry = ToolRegistry()

    definition = ToolDefinition(
        name="example_search",
        description="Example search tool.",
        arguments_model=ExampleArguments,
        handler=example_handler,
    )

    registry.register(definition)

    with pytest.raises(ToolRegistrationError):

        registry.register(definition)


def test_rejects_invalid_tool_name():

    with pytest.raises(ToolRegistrationError):

        ToolDefinition(
            name="Invalid Tool",
            description="Invalid name.",
            arguments_model=ExampleArguments,
            handler=example_handler,
        )


def test_rejects_non_pydantic_arguments():

    with pytest.raises(ToolRegistrationError):

        ToolDefinition(
            name="example_search",
            description="Example search.",
            arguments_model=dict,
            handler=example_handler,
        )


def test_rejects_synchronous_handler():

    def sync_handler(arguments, context):
        return {}

    with pytest.raises(ToolRegistrationError):

        ToolDefinition(
            name="example_search",
            description="Example search.",
            arguments_model=ExampleArguments,
            handler=sync_handler,
        )


def test_disabled_tool_is_not_available():

    registry = ToolRegistry()

    definition = ToolDefinition(
        name="example_search",
        description="Example search.",
        arguments_model=ExampleArguments,
        handler=example_handler,
        enabled=False,
    )

    registry.register(definition)

    assert registry.get("example_search") is None


def test_public_definition_does_not_expose_handler():

    definition = ToolDefinition(
        name="example_search",
        description="Example search.",
        arguments_model=ExampleArguments,
        handler=example_handler,
    )

    public_definition = definition.public_definition()

    assert public_definition.name == "example_search"

    assert not hasattr(
        public_definition,
        "handler",
    )

    assert "properties" in (
        public_definition.parameters_schema
    )