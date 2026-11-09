from pydantic import BaseModel, ConfigDict, Field

from app.schemas.llm_tools import (
    ToolExecutionContext,
)

from app.services.llm_tools.tool_registry import (
    ToolDefinition,
    tool_registry,
)


class AcademicSearchArguments(BaseModel):

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=3,
        max_length=300,
    )

    subject: str | None = Field(
        default=None,
        max_length=100,
    )


async def academic_search_placeholder(
    arguments: AcademicSearchArguments,
    context: ToolExecutionContext,
) -> dict:

    """
    Placeholder demonstrating the registered tool contract.

    Real academic search implementation belongs to Phase 17.7.
    """

    return {
        "status": "placeholder",
        "query": arguments.query,
        "subject": arguments.subject,
        "message": (
            "Academic search integration has not "
            "been implemented yet."
        ),
    }


def register_example_tools() -> None:

    if tool_registry.contains("academic_search"):

        return

    tool_registry.register(
        ToolDefinition(
            name="academic_search",
            description=(
                "Search for academic learning resources "
                "using a student query and optional subject."
            ),
            arguments_model=AcademicSearchArguments,
            handler=academic_search_placeholder,
            requires_authenticated_user=False,
        )
    )