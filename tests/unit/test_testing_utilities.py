import pytest

from tests.support.utilities import (
    assert_mapping_contains,
    assert_raises_with_message,
    normalize_text,
)


def test_mapping_contains_expected_values():
    actual = {
        "name": "ScholarAI",
        "status": "active",
        "version": 1,
    }

    expected = {
        "name": "ScholarAI",
        "status": "active",
    }

    assert_mapping_contains(actual, expected)


def test_mapping_rejects_missing_key():
    with pytest.raises(AssertionError):
        assert_mapping_contains(
            {"name": "ScholarAI"},
            {"status": "active"},
        )


def test_mapping_rejects_incorrect_value():
    with pytest.raises(AssertionError):
        assert_mapping_contains(
            {"status": "failed"},
            {"status": "passed"},
        )


def test_assert_raises_with_message():
    def operation():
        raise ValueError("Invalid document identifier.")

    exception = assert_raises_with_message(
        ValueError,
        operation,
        "Invalid document",
    )

    assert isinstance(exception, ValueError)


def test_assert_raises_rejects_wrong_exception():
    def operation():
        raise TypeError("Invalid type.")

    with pytest.raises(AssertionError):
        assert_raises_with_message(
            ValueError,
            operation,
            "Invalid",
        )


def test_assert_raises_rejects_missing_exception():
    def operation():
        return True

    with pytest.raises(AssertionError):
        assert_raises_with_message(
            ValueError,
            operation,
            "Invalid",
        )


def test_normalize_text_removes_extra_whitespace():
    result = normalize_text(
        "ScholarAI     is   an AI     study platform."
    )

    assert result == "ScholarAI is an AI study platform."


def test_normalize_text_handles_newlines():
    result = normalize_text(
        "ScholarAI\nis\tan AI\nstudy platform."
    )

    assert result == "ScholarAI is an AI study platform."


def test_normalize_text_rejects_non_string():
    with pytest.raises(TypeError):
        normalize_text(123)
