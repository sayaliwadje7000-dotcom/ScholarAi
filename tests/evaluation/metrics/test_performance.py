import pytest

from app.evaluation.metrics.performance import (
    latency_statistics,
    reliability,
)


def test_latency_statistics():
    result = latency_statistics(
        [10, 20, 30, 40, 50]
    )

    assert result["mean"] == pytest.approx(30)
    assert result["median"] == pytest.approx(30)
    assert result["p95"] == pytest.approx(48)


def test_reliability():
    result = reliability(
        succeeded=90,
        failed=5,
        timed_out=5,
    )

    assert result["success_rate"] == pytest.approx(0.9)
    assert result["failure_rate"] == pytest.approx(0.05)
    assert result["timeout_rate"] == pytest.approx(0.05)