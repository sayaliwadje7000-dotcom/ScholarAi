import pytest

from app.services.response_intelligence.response_normalizer import (
    ResponseNormalizer,
)


@pytest.fixture
def normalizer():

    return ResponseNormalizer()


def test_removes_leading_and_trailing_whitespace(normalizer):

    result = normalizer.normalize(
        "   Hello ScholarAI.   "
    )

    assert result == "Hello ScholarAI."


def test_normalizes_windows_line_endings(normalizer):

    result = normalizer.normalize(
        "Heading\r\n\r\nContent"
    )

    assert result == "Heading\n\nContent"


def test_removes_excessive_blank_lines(normalizer):

    result = normalizer.normalize(
        "First paragraph\n\n\n\nSecond paragraph"
    )

    assert result == (
        "First paragraph\n\nSecond paragraph"
    )


def test_preserves_markdown_headings(normalizer):

    response = (
        "# Binary Search\n\n"
        "## Working\n\n"
        "Binary search divides the search space."
    )

    result = normalizer.normalize(response)

    assert "# Binary Search" in result

    assert "## Working" in result


def test_preserves_code_indentation(normalizer):

    response = (
        "Example:\n"
        "```python\n"
        "def search():\n"
        "    return True\n"
        "```"
    )

    result = normalizer.normalize(response)

    assert "    return True" in result


def test_rejects_non_string_response(normalizer):

    with pytest.raises(ValueError):

        normalizer.normalize(None)