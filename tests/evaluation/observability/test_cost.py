import pytest

from app.evaluation.observability.cost import (
    CostEvaluationError,
    calculate_average_cost,
    calculate_total_cost,
    estimate_cost_for_model,
    estimate_model_cost,
)

from app.evaluation.observability.schemas import ModelPricing


def make_pricing():
    return ModelPricing(
        model_name="test-model",
        input_cost_per_1k_tokens=0.01,
        output_cost_per_1k_tokens=0.02,
    )


def test_estimate_model_cost():
    result = estimate_model_cost(
        input_tokens=1000,
        output_tokens=500,
        pricing=make_pricing(),
    )

    assert result == pytest.approx(0.02)


def test_estimate_zero_token_cost():
    assert estimate_model_cost(
        input_tokens=0,
        output_tokens=0,
        pricing=make_pricing(),
    ) == 0


def test_reject_negative_token_counts():
    with pytest.raises(CostEvaluationError):
        estimate_model_cost(
            input_tokens=-1,
            output_tokens=100,
            pricing=make_pricing(),
        )


def test_estimate_cost_for_registered_model():
    registry = {"test-model": make_pricing()}

    result = estimate_cost_for_model(
        "test-model",
        1000,
        500,
        registry,
    )

    assert result == pytest.approx(0.02)


def test_missing_model_pricing():
    with pytest.raises(CostEvaluationError):
        estimate_cost_for_model(
            "unknown-model",
            100,
            100,
            {},
        )


def test_calculate_total_cost():
    assert calculate_total_cost([0.1, 0.2, 0.3]) == pytest.approx(0.6)


def test_calculate_average_cost():
    assert calculate_average_cost([0.1, 0.2, 0.3]) == pytest.approx(0.2)


def test_average_cost_empty():
    assert calculate_average_cost([]) == 0


def test_reject_negative_cost():
    with pytest.raises(CostEvaluationError):
        calculate_total_cost([0.1, -0.2])
