import asyncio

import pytest

from app.evaluation.core import (

    EvaluationConfig,
    EvaluationOrchestrator,
    EvaluationRegistry,

    EvaluationStatus,
    EvaluationLifecycle,

    Evaluator,
    EvaluatorType,

)

from app.evaluation.core.exceptions import (

    DuplicateEvaluatorError,
    EvaluationExecutionError,
    EvaluationTimeoutError,

    InvalidEvaluationTransitionError,
    UnknownEvaluatorError,

)

from app.evaluation.adapters import (
    CallableEvaluatorAdapter
)


def make_adapter(
    fn=lambda payload: {"accuracy": 0.9}
):

    return CallableEvaluatorAdapter(

        "sample",

        EvaluatorType.CUSTOM,

        fn

    )


def test_registry_registration_lookup_and_type_filter():

    registry = EvaluationRegistry()

    adapter = make_adapter()

    registry.register(adapter)

    assert registry.get("sample") is adapter

    assert registry.exists("sample")

    assert registry.get_by_type(
        EvaluatorType.CUSTOM
    ) == (adapter,)

    assert registry.get_all() == (adapter,)


def test_registry_rejects_duplicates_and_unknown_ids():

    registry = EvaluationRegistry()

    registry.register(
        make_adapter()
    )

    with pytest.raises(
        DuplicateEvaluatorError
    ):

        registry.register(
            make_adapter()
        )

    with pytest.raises(
        UnknownEvaluatorError
    ):

        registry.get("missing")


def test_registry_unregister():

    registry = EvaluationRegistry()

    registry.register(
        make_adapter()
    )

    registry.unregister("sample")

    assert not registry.exists("sample")


def test_config_validation_and_serialization():

    config = EvaluationConfig(

        evaluator_id="sample",

        timeout_seconds=3,

        tags={
            "phase": "19.1"
        }

    )

    assert config.to_dict()[
        "timeout_seconds"
    ] == 3

    with pytest.raises(ValueError):

        EvaluationConfig(
            evaluator_id="sample",
            timeout_seconds=0
        )

    with pytest.raises(ValueError):

        EvaluationConfig(
            evaluator_id="sample",
            max_retries=-1
        )


def test_lifecycle_enforces_transitions():

    state = EvaluationLifecycle()

    state.transition(
        EvaluationStatus.RUNNING
    )

    state.transition(
        EvaluationStatus.COMPLETED
    )

    assert state.history == (

        EvaluationStatus.PENDING,

        EvaluationStatus.RUNNING,

        EvaluationStatus.COMPLETED,

    )

    with pytest.raises(
        InvalidEvaluationTransitionError
    ):

        state.transition(
            EvaluationStatus.FAILED
        )


def test_orchestrator_executes_and_normalizes():

    registry = EvaluationRegistry()

    registry.register(
        make_adapter()
    )

    result = EvaluationOrchestrator(
        registry
    ).run_sync(

        EvaluationConfig(

            evaluator_id="sample",

            dataset_name="smoke",

            dataset_version="1"

        ),

        {
            "question": "test"
        }

    )

    assert result.status == "completed"

    assert result.metrics == {
        "accuracy": 0.9
    }

    assert result.dataset_name == "smoke"

    assert result.execution_id

    assert result.duration_ms >= 0

    assert result.to_dict()["started_at"]


def test_orchestrator_accepts_pydantic_like_to_dict():

    class Report:

        def to_dict(self):

            return {
                "ndcg_at_5": 0.75
            }

    registry = EvaluationRegistry()

    registry.register(
        make_adapter(
            lambda _: Report()
        )
    )

    result = EvaluationOrchestrator(
        registry
    ).run_sync(

        EvaluationConfig(
            evaluator_id="sample"
        ),

        {
            "x": 1
        }

    )

    assert result.metrics[
        "ndcg_at_5"
    ] == 0.75


def test_orchestrator_wraps_evaluator_failure():

    registry = EvaluationRegistry()

    def fail(_):

        raise ValueError(
            "private payload should not enter public error"
        )

    registry.register(
        make_adapter(fail)
    )

    with pytest.raises(
        EvaluationExecutionError
    ):

        EvaluationOrchestrator(
            registry
        ).run_sync(

            EvaluationConfig(
                evaluator_id="sample"
            ),

            {
                "x": 1
            }

        )


def test_orchestrator_timeout():

    registry = EvaluationRegistry()

    async def slow(_):

        await asyncio.sleep(0.05)

        return {
            "ok": True
        }

    registry.register(
        make_adapter(slow)
    )

    with pytest.raises(
        EvaluationTimeoutError
    ):

        EvaluationOrchestrator(
            registry
        ).run_sync(

            EvaluationConfig(

                evaluator_id="sample",

                timeout_seconds=0.001

            ),

            {
                "x": 1
            }

        )


def test_orchestrator_rejects_non_finite_metrics():

    registry = EvaluationRegistry()

    registry.register(

        make_adapter(
            lambda _: {
                "score": float("nan")
            }
        )

    )

    with pytest.raises(
        EvaluationExecutionError
    ):

        EvaluationOrchestrator(
            registry
        ).run_sync(

            EvaluationConfig(
                evaluator_id="sample"
            ),

            {
                "x": 1
            }

        )


def test_run_sync_rejects_nested_event_loop():

    registry = EvaluationRegistry()

    registry.register(
        make_adapter()
    )

    orchestrator = EvaluationOrchestrator(
        registry
    )

    async def call():

        with pytest.raises(RuntimeError):

            orchestrator.run_sync(

                EvaluationConfig(
                    evaluator_id="sample"
                ),

                {}

            )

    asyncio.run(call())