import pytest

from app.evaluation.metrics.classification import (
    accuracy,
    precision_recall_f1,
    balanced_accuracy,
    confusion_matrix,
)


def test_accuracy():
    assert accuracy(
        [1, 1, 0, 0],
        [1, 0, 0, 0],
    ) == pytest.approx(0.75)


def test_binary_precision_recall_f1():
    result = precision_recall_f1(
        [0, 1, 1, 0],
        [0, 1, 0, 0],
        average="binary",
        positive_label=1,
    )

    assert result["precision"] == pytest.approx(1.0)
    assert result["recall"] == pytest.approx(0.5)
    assert result["f1"] == pytest.approx(2 / 3)


def test_macro_precision_recall_f1():
    result = precision_recall_f1(
        [1, 1, 0, 0],
        [1, 0, 0, 0],
        average="macro",
    )

    assert result["precision"] == pytest.approx(5 / 6)
    assert result["recall"] == pytest.approx(0.75)
    assert result["f1"] == pytest.approx(11 / 15)


def test_balanced_accuracy():
    assert balanced_accuracy(
        [0, 0, 1, 1],
        [0, 0, 1, 0],
    ) == pytest.approx(0.75)


def test_confusion_matrix():
    result = confusion_matrix(
        [0, 1, 1, 0],
        [0, 1, 0, 0],
    )

    assert result == {
        0: {0: 2, 1: 0},
        1: {0: 1, 1: 1},
    }