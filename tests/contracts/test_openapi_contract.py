import pytest

from app.main import app

from tests.contracts.openapi_utils import (
    collect_schema_references,
    get_openapi_operations,
    resolve_schema_reference,
)


@pytest.fixture(scope="module")
def openapi_schema():
    return app.openapi()


def test_openapi_document_is_generated(openapi_schema):
    assert isinstance(openapi_schema, dict)
    assert "openapi" in openapi_schema
    assert "info" in openapi_schema
    assert "paths" in openapi_schema


def test_openapi_has_api_metadata(openapi_schema):
    info = openapi_schema["info"]

    assert isinstance(info.get("title"), str)
    assert info["title"].strip()

    assert isinstance(info.get("version"), str)
    assert info["version"].strip()


def test_openapi_contains_registered_endpoints(openapi_schema):
    operations = get_openapi_operations(openapi_schema)

    assert operations, "No HTTP operations were found in OpenAPI."


def test_every_operation_has_operation_id(openapi_schema):
    operations = get_openapi_operations(openapi_schema)

    missing_operation_ids = [
        f"{item['method'].upper()} {item['path']}"
        for item in operations
        if not item["operation"].get("operationId")
    ]

    assert not missing_operation_ids, (
        "Operations missing operationId: "
        f"{missing_operation_ids}"
    )


def test_every_operation_documents_responses(openapi_schema):
    operations = get_openapi_operations(openapi_schema)

    for item in operations:
        operation = item["operation"]

        assert isinstance(operation.get("responses"), dict), (
            f"{item['method'].upper()} {item['path']} "
            "does not document responses."
        )

        assert operation["responses"], (
            f"{item['method'].upper()} {item['path']} "
            "has an empty response definition."
        )


def test_every_documented_response_has_description(openapi_schema):
    operations = get_openapi_operations(openapi_schema)

    for item in operations:
        for status, response in item["operation"]["responses"].items():
            assert isinstance(response, dict), (
                f"Invalid response definition for "
                f"{item['method'].upper()} {item['path']} "
                f"status {status}."
            )

            assert isinstance(response.get("description"), str), (
                f"Missing response description for "
                f"{item['method'].upper()} {item['path']} "
                f"status {status}."
            )


def test_all_local_schema_references_resolve(openapi_schema):
    references = collect_schema_references(openapi_schema)

    for reference in references:
        if reference.startswith("#/"):
            resolve_schema_reference(
                openapi_schema,
                reference,
            )


def test_openapi_contains_component_schemas(openapi_schema):
    components = openapi_schema.get("components", {})
    schemas = components.get("schemas", {})

    assert isinstance(schemas, dict)
    assert schemas, "OpenAPI contains no component schemas."
