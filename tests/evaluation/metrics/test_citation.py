import pytest

from app.evaluation.metrics.citation import (
    citation_precision,
    citation_recall,
    citation_coverage,
)


def test_citation_precision():
    assert citation_precision(
        ["a", "b", "c"],
        ["a", "b"],
    ) == pytest.approx(2 / 3)


def test_citation_recall():
    assert citation_recall(
        ["a", "b", "c"],
        ["a", "b"],
    ) == pytest.approx(2 / 3)


def test_citation_coverage():
    assert citation_coverage(
        ["a", "b", "c"],
        ["a", "b"],
    ) == pytest.approx(2 / 3)