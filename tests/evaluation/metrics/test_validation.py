import pytest

from app.evaluation.metrics.validation import (
    validate_non_empty,
    validate_same_length,
    validate_positive_k,
)


def test_validate_non_empty():
    assert validate_non_empty([1, 2, 3]) == [1, 2, 3]


def test_validate_empty_rejected():
    with pytest.raises(ValueError):
        validate_non_empty([])


def test_validate_same_length():
    validate_same_length([1, 2], [1, 2])


def test_validate_different_lengths():
    with pytest.raises(ValueError):
        validate_same_length([1], [1, 2])


def test_validate_positive_k():
    assert validate_positive_k(5) == 5


@pytest.mark.parametrize("k", [0, -1, 1.5, True])
def test_invalid_k_rejected(k):
    with pytest.raises(ValueError):
        validate_positive_k(k)