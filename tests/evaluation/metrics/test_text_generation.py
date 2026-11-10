import pytest

from app.evaluation.metrics.text_generation import (
    exact_match,
    token_precision,
    token_recall,
    token_f1,
)


def test_exact_match():
    assert exact_match(
        "The answer is 42",
        "The answer is 42",
    ) == 1.0


def test_exact_match_case_insensitive():
    assert exact_match(
        "HELLO WORLD",
        "hello world",
    ) == 1.0


def test_token_precision():
    assert token_precision(
        "AI helps students",
        "AI helps students learn",
    ) == pytest.approx(1.0)


def test_token_recall():
    assert token_recall(
        "AI helps students",
        "AI helps students learn",
    ) == pytest.approx(0.75)


def test_token_f1():
    assert token_f1(
        "AI helps students",
        "AI helps students learn",
    ) == pytest.approx(6 / 7)