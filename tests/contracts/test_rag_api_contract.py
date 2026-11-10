import pytest

from app.main import app


@pytest.fixture(scope="module")
def rag_operation():
    openapi_schema = app.openapi()

    matching_operations = []

    for path, path_item in openapi_schema.get("paths", {}).items():
        if not path.rstrip("/").endswith("/ask"):
            continue

        post_operation = path_item.get("post")

        if post_operation:
            matching_operations.append(
                {
                    "path": path,
                    "operation": post_operation,
                }
            )

    assert matching_operations, (
        "Could not locate the registered RAG POST /ask endpoint."
    )

    assert len(matching_operations) == 1, (
        "Expected exactly one registered RAG POST /ask endpoint."
    )

    return matching_operations[0]


def test_rag_endpoint_has_request_body(rag_operation):
    operation = rag_operation["operation"]

    request_body = operation.get("requestBody")

    assert request_body is not None
    assert request_body.get("content")


def test_rag_endpoint_request_body_has_schema(rag_operation):
    request_body = rag_operation["operation"]["requestBody"]

    content = request_body["content"]

    json_content = content.get("application/json")

    assert json_content is not None
    assert isinstance(json_content.get("schema"), dict)


def test_rag_endpoint_documents_success_response(rag_operation):
    responses = rag_operation["operation"].get("responses", {})

    assert "200" in responses, (
        "RAG endpoint must document its successful 200 response."
    )


def test_rag_endpoint_success_response_has_schema(rag_operation):
    response = rag_operation["operation"]["responses"]["200"]

    json_content = response.get("content", {}).get(
        "application/json"
    )

    assert json_content is not None
    assert isinstance(json_content.get("schema"), dict)


def test_rag_endpoint_documents_validation_failure(rag_operation):
    responses = rag_operation["operation"].get("responses", {})

    assert "422" in responses, (
        "RAG endpoint must document request validation failures."
    )


def test_rag_endpoint_has_operation_identifier(rag_operation):
    operation = rag_operation["operation"]

    assert operation.get("operationId")
