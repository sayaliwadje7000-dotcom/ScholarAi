import re

from typing import (
    Any,
    Awaitable,
    Callable,
    Type,
)

from pydantic import BaseModel

from app.schemas.llm_tools import (
    ToolDefinitionResponse,
)

from app.services.llm_tools.exceptions import (
    ToolRegistrationError,
)


ToolHandler = Callable[
    [BaseModel, Any],
    Awaitable[Any],
]


class ToolDefinition:

    def __init__(
        self,
        name: str,
        description: str,
        arguments_model: Type[BaseModel],
        handler: ToolHandler,
        requires_authenticated_user: bool = False,
        enabled: bool = True,
    ):

        if not re.fullmatch(
            r"[a-z][a-z0-9_]*",
            name,
        ):
            raise ToolRegistrationError(
                "Invalid tool name."
            )

        if not description.strip():
            raise ToolRegistrationError(
                "Tool description cannot be empty."
            )

        if not isinstance(
            arguments_model,
            type,
        ) or not issubclass(
            arguments_model,
            BaseModel,
        ):
            raise ToolRegistrationError(
                "Tool arguments must use a Pydantic model."
            )

        if not callable(handler):
            raise ToolRegistrationError(
                "Tool handler must be callable."
            )

        if not __import__("inspect").iscoroutinefunction(
            handler
        ):
            raise ToolRegistrationError(
                "Tool handlers must be asynchronous."
            )

        self.name = name
        self.description = description.strip()
        self.arguments_model = arguments_model
        self.handler = handler
        self.requires_authenticated_user = (
            requires_authenticated_user
        )
        self.enabled = enabled

    def public_definition(self) -> ToolDefinitionResponse:

        return ToolDefinitionResponse(
            name=self.name,
            description=self.description,
            parameters_schema=(
                self.arguments_model.model_json_schema()
            ),
            requires_authenticated_user=(
                self.requires_authenticated_user
            ),
            enabled=self.enabled,
        )


class ToolRegistry:

    def __init__(self):

        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        definition: ToolDefinition,
    ) -> None:

        if definition.name in self._tools:
            raise ToolRegistrationError(
                f"Tool '{definition.name}' is already registered."
            )

        self._tools[definition.name] = definition

    def get(
        self,
        name: str,
    ) -> ToolDefinition | None:

        definition = self._tools.get(name)

        if definition is None:
            return None

        if not definition.enabled:
            return None

        return definition

    def list_enabled(self) -> list[ToolDefinitionResponse]:

        return [
            definition.public_definition()
            for definition in self._tools.values()
            if definition.enabled
        ]

    def contains(self, name: str) -> bool:

        return name in self._tools

    def clear(self) -> None:

        self._tools.clear()


tool_registry = ToolRegistry()