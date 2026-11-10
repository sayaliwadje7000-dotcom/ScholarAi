from typing import Any


def get_openapi_operations(openapi_schema: dict[str, Any]):
    """Return all HTTP operations declared in an OpenAPI document."""
    operations = []

    paths = openapi_schema.get("paths", {})

    supported_methods = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "options",
        "head",
        "trace",
    }

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            if method.lower() not in supported_methods:
                continue

            if isinstance(operation, dict):
                operations.append(
                    {
                        "path": path,
                        "method": method.lower(),
                        "operation": operation,
                    }
                )

    return operations


def resolve_schema_reference(
    openapi_schema: dict[str, Any],
    reference: str,
) -> dict[str, Any]:
    """Resolve a local JSON reference in an OpenAPI document."""
    if not reference.startswith("#/"):
        raise ValueError(
            f"External schema references are not supported: {reference}"
        )

    current = openapi_schema

    for part in reference[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")

        if not isinstance(current, dict) or part not in current:
            raise KeyError(
                f"Unresolvable OpenAPI reference: {reference}"
            )

        current = current[part]

    if not isinstance(current, dict):
        raise TypeError(
            f"Referenced OpenAPI object is not a schema: {reference}"
        )

    return current


def collect_schema_references(value: Any) -> list[str]:
    """Recursively collect local and external JSON schema references."""
    references = []

    if isinstance(value, dict):
        reference = value.get("$ref")

        if isinstance(reference, str):
            references.append(reference)

        for nested_value in value.values():
            references.extend(
                collect_schema_references(nested_value)
            )

    elif isinstance(value, list):
        for nested_value in value:
            references.extend(
                collect_schema_references(nested_value)
            )

    return references


def get_success_responses(
    operation: dict[str, Any],
) -> dict[str, Any]:
    """Return documented successful HTTP responses."""
    responses = operation.get("responses", {})

    return {
        status: response
        for status, response in responses.items()
        if str(status).startswith("2")
    }
