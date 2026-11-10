import pytest

from app.evaluation.metrics.registry import MetricRegistry


def test_metric_registration_and_lookup():
    registry = MetricRegistry()

    metric = lambda: 0.95

    registry.register("accuracy", metric)

    assert registry.get("accuracy") is metric


def test_duplicate_metric_rejected():
    registry = MetricRegistry()

    registry.register("accuracy", lambda: 0.95)

    with pytest.raises(ValueError):
        registry.register("accuracy", lambda: 0.90)


def test_missing_metric_returns_none():
    registry = MetricRegistry()

    assert registry.get("unknown") is None