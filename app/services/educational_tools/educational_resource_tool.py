import logging

from app.schemas.educational_resource_discovery import (
    ResourceDiscoveryRequest,
)

from app.schemas.educational_tool_schemas import (
    EducationalResourceSearchArguments,
    EducationalResourceToolOutput,
)

from app.services.llm_tools.tool_registry import (
    ToolDefinition,
    ToolRegistry,
    tool_registry,
)


logger = logging.getLogger(__name__)


EDUCATIONAL_RESOURCE_TOOL_NAME = (
    "educational_resource_search"
)


def create_educational_resource_handler(
    discovery_service,
):
    """
    Creates an asynchronous tool handler around the existing
    ResourceDiscoveryService.

    Dependency injection ensures that this module does not
    create a second provider registry or discovery service.
    """

    async def educational_resource_search_handler(
        arguments: EducationalResourceSearchArguments,
        context,
    ) -> dict:

        logger.info(
            "Educational resource search requested: "
            "request_id=%s",
            context.request_id,
        )

        discovery_request = ResourceDiscoveryRequest(
            query=arguments.query,
            providers=arguments.providers,
            resource_types=arguments.resource_types,
            subject=arguments.subject,
            language=arguments.language,
            limit_per_provider=arguments.limit_per_provider,
        )

        response = await discovery_service.discover(
            discovery_request
        )

        # Convert the existing Pydantic response into
        # JSON-compatible structured output.
        response_data = response.model_dump(
            mode="json"
        )

        # Validate the integration boundary before returning.
        validated_output = (
            EducationalResourceToolOutput.model_validate(
                response_data
            )
        )

        logger.info(
            "Educational resource search completed: "
            "request_id=%s results=%s",
            context.request_id,
            validated_output.total_results,
        )

        return validated_output.model_dump(
            mode="json"
        )

    return educational_resource_search_handler


def register_educational_resource_tool(
    discovery_service,
    registry: ToolRegistry = tool_registry,
) -> None:
    """
    Register the real educational resource discovery tool.

    Registration is explicit. It should be performed during
    controlled application startup after the discovery service
    has been configured.
    """

    if registry.contains(
        EDUCATIONAL_RESOURCE_TOOL_NAME
    ):

        raise ValueError(
            "Educational resource search tool is already registered."
        )

    handler = create_educational_resource_handler(
        discovery_service
    )

    definition = ToolDefinition(
        name=EDUCATIONAL_RESOURCE_TOOL_NAME,
        description=(
            "Search educational resources across configured "
            "academic and educational providers. Supports "
            "query, subject, language, provider and resource "
            "type filters. Returns normalized and deduplicated "
            "educational resources."
        ),
        arguments_model=EducationalResourceSearchArguments,
        handler=handler,
        requires_authenticated_user=False,
        enabled=True,
    )

    registry.register(
        definition
    )