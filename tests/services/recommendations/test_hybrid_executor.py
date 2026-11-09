import pytest

from app.services.recommendations.hybrid_executor import (
    HybridExecutor,
)


class FakeOrchestrator:
    def __init__(self):
        self.calls = []

    def execute(self, context, limit=None):
        self.calls.append((context, limit))
        return {"status": "success"}


def test_executor_delegates_to_phase_15_orchestrator():
    orchestrator = FakeOrchestrator()
    executor = HybridExecutor(orchestrator)

    context = object()

    result = executor(context, limit=5)

    assert result == {"status": "success"}
    assert orchestrator.calls == [(context, 5)]


def test_executor_supports_default_limit():
    orchestrator = FakeOrchestrator()
    executor = HybridExecutor(orchestrator)

    context = object()

    executor(context)

    assert orchestrator.calls == [(context, None)]


def test_executor_rejects_missing_orchestrator():
    with pytest.raises(ValueError):
        HybridExecutor(None)


def test_executor_rejects_orchestrator_without_execute():
    with pytest.raises(TypeError):
        HybridExecutor(object())