import pytest

from app.services.response_intelligence.response_parser import (
    ResponseParser,
)

from app.services.response_intelligence.exceptions import (
    ResponseParsingError,
    ResponseValidationError,
)


@pytest.fixture
def parser():

    return ResponseParser()


def valid_payload():

    return {
        "answer": "Binary search is an efficient searching algorithm.",
        "key_points": [
            "Requires sorted data.",
            "Uses divide and conquer.",
        ],
        "examples": [
            "Searching for an element in a sorted array."
        ],
        "caveats": [
            "Does not directly apply to unsorted arrays."
        ],
        "conclusion": "Binary search reduces the search space.",
    }


def test_parses_valid_json(parser):

    import json

    result = parser.parse(
        json.dumps(valid_payload())
    )

    assert result.answer.startswith(
        "Binary search"
    )

    assert len(result.key_points) == 2


def test_parses_markdown_json_fence(parser):

    import json

    response = (
        "```json\n"
        + json.dumps(valid_payload())
        + "\n```"
    )

    result = parser.parse(response)

    assert result.answer.startswith(
        "Binary search"
    )


def test_rejects_invalid_json(parser):

    with pytest.raises(ResponseParsingError):

        parser.parse(
            '{"answer": invalid}'
        )


def test_rejects_non_object_json(parser):

    with pytest.raises(ResponseParsingError):

        parser.parse(
            '["answer", "example"]'
        )


def test_rejects_missing_required_answer(parser):

    import json

    payload = valid_payload()

    del payload["answer"]

    with pytest.raises(ResponseValidationError):

        parser.parse(
            json.dumps(payload)
        )


def test_rejects_unexpected_fields(parser):

    import json

    payload = valid_payload()

    payload["unexpected"] = "value"

    with pytest.raises(ResponseValidationError):

        parser.parse(
            json.dumps(payload)
        )


def test_rejects_empty_key_point(parser):

    import json

    payload = valid_payload()

    payload["key_points"] = [""]

    with pytest.raises(ResponseValidationError):

        parser.parse(
            json.dumps(payload)
        )