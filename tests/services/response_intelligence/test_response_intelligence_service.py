import json

import pytest

from app.schemas.response_intelligence import (
    ResponseFormat,
    ResponseIntelligenceRequest,
    ResponseValidationStatus,
)

from app.services.response_intelligence.response_intelligence_service import (
    ResponseIntelligenceService,
)

from app.services.response_intelligence.exceptions import (
    ResponseParsingError,
    ResponseSafetyError,
)


@pytest.fixture
def service():

    return ResponseIntelligenceService()


def structured_response():

    return {
        "answer": (
            "Binary search is an algorithm that "
            "searches sorted data by repeatedly "
            "dividing the search interval."
        ),
        "key_points": [
            "Requires sorted data.",
            "Uses divide and conquer.",
        ],
        "examples": [
            "Searching a sorted array."
        ],
        "caveats": [
            "Unsorted data must be sorted first."
        ],
        "conclusion": (
            "Binary search is efficient for sorted data."
        ),
    }


def test_processes_plain_text(service):

    request = ResponseIntelligenceRequest(
        response="  Binary search is efficient.  ",
        response_format=ResponseFormat.PLAIN_TEXT,
        validate_safety=False,
    )

    result = service.process(request)

    assert result.response == (
        "Binary search is efficient."
    )

    assert result.validation_status == (
        ResponseValidationStatus.VALID
    )

    assert result.word_count == 4


def test_processes_structured_academic_response(service):

    request = ResponseIntelligenceRequest(
        response=json.dumps(
            structured_response()
        ),
        response_format=ResponseFormat.ACADEMIC,
        validate_safety=False,
    )

    result = service.process(request)

    assert result.structured_response is not None

    assert "## Key Points" in result.response

    assert "## Examples" in result.response

    assert "## Conclusion" in result.response

    assert result.validation_status == (
        ResponseValidationStatus.VALID
    )


def test_rejects_invalid_structured_response(service):

    request = ResponseIntelligenceRequest(
        response="This is not JSON.",
        response_format=ResponseFormat.ACADEMIC,
        validate_safety=False,
    )

    with pytest.raises(ResponseParsingError):

        service.process(request)


def test_returns_quality_issues(service):

    request = ResponseIntelligenceRequest(
        response="This is a comparison.",
        response_format=ResponseFormat.COMPARISON,
        validate_safety=False,
    )

    result = service.process(request)

    assert result.validation_status == (
        ResponseValidationStatus.PARTIALLY_VALID
    )

    assert len(result.quality_issues) > 0


def test_calculates_response_metadata(service):

    request = ResponseIntelligenceRequest(
        response="Binary search is efficient.",
        validate_safety=False,
    )

    result = service.process(request)

    assert result.character_count == len(result.response)

    assert result.word_count == len(
        result.response.split()
    )


def test_rejects_output_when_safety_validation_fails(
    service,
    monkeypatch,
):

    from types import SimpleNamespace

    def fake_validate_output(response):

        return SimpleNamespace(
            allowed=False,
        )

    monkeypatch.setattr(
        "app.services.response_intelligence.response_intelligence_service.validate_output",
        fake_validate_output,
    )

    request = ResponseIntelligenceRequest(
        response="A generated response.",
        validate_safety=True,
    )

    with pytest.raises(ResponseSafetyError):

        service.process(request)