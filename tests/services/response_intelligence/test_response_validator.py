import pytest

from app.schemas.response_intelligence import (
    ResponseFormat,
)

from app.services.response_intelligence.response_validator import (
    ResponseValidator,
)

from app.services.response_intelligence.exceptions import (
    ResponseQualityError,
)


@pytest.fixture
def validator():

    return ResponseValidator()


def test_accepts_valid_plain_text(validator):

    issues = validator.validate(
        "Binary search is an efficient searching algorithm.",
        ResponseFormat.PLAIN_TEXT,
    )

    assert issues == []


def test_detects_unmatched_code_fence(validator):

    issues = validator.validate(
        "Example:\n```python\nprint('hello')",
        ResponseFormat.PLAIN_TEXT,
    )

    assert any(
        "unmatched code fence" in issue
        for issue in issues
    )


def test_detects_missing_comparison_structure(validator):

    issues = validator.validate(
        "Binary search is an efficient algorithm.",
        ResponseFormat.COMPARISON,
    )

    assert any(
        "comparison structure" in issue
        for issue in issues
    )


def test_accepts_comparison_structure(validator):

    issues = validator.validate(
        "Binary search and linear search differ in complexity.",
        ResponseFormat.COMPARISON,
    )

    assert issues == []


def test_detects_missing_steps(validator):

    issues = validator.validate(
        "Binary search is an efficient algorithm.",
        ResponseFormat.STEP_BY_STEP,
    )

    assert any(
        "sequence" in issue
        for issue in issues
    )


def test_rejects_empty_response(validator):

    with pytest.raises(ResponseQualityError):

        validator.validate(
            " ",
            ResponseFormat.PLAIN_TEXT,
        )


def test_rejects_oversized_response(validator):

    with pytest.raises(ResponseQualityError):

        validator.validate(
            "A" * 50001,
            ResponseFormat.PLAIN_TEXT,
        )