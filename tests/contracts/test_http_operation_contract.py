import pytest

from app.main import app

from tests.contracts.openapi_utils import (
    get_openapi_operations,
    get_success_responses,
)


@pytest.fixture(scope="module")
def operations():
    return get_openapi_operations(app.openapi())


def test_all_operations_have_documented_success_responses(operations):
    failures = []

    for item in operations:
        success_responses = get_success_responses(
            item["operation"]
        )

        if not success_responses:
            failures.append(
                f"{item['method'].upper()} {item['path']}"
            )

    assert not failures, (
        "Operations without documented successful responses: "
        f"{failures}"
    )


def test_operations_with_request_bodies_document_content(operations):
    for item in operations:
        operation = item["operation"]
        request_body = operation.get("requestBody")

        if request_body is None:
            continue

        content = request_body.get("content", {})

        assert content, (
            f"{item['method'].upper()} {item['path']} "
            "has an empty request body content definition."
        )

        for media_type, media_definition in content.items():
            assert isinstance(media_definition, dict), (
                f"Invalid request media definition: "
                f"{item['path']} {media_type}"
            )


def test_success_responses_with_content_have_media_types(operations):
    for item in operations:
        success_responses = get_success_responses(
            item["operation"]
        )

        for status, response in success_responses.items():
            content = response.get("content", {})

            if not content:
                continue

            assert isinstance(content, dict), (
                f"Invalid response content for "
                f"{item['method'].upper()} {item['path']} "
                f"status {status}."
            )

            assert content, (
                f"Empty response content for "
                f"{item['method'].upper()} {item['path']} "
                f"status {status}."
            )
