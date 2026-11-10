import pytest

from app.evaluation.metrics.cost import (
    TokenPricing,
    estimate_cost,
)


def test_token_pricing():
    pricing = TokenPricing(
        input_cost_per_million=2.0,
        output_cost_per_million=8.0,
    )

    assert pricing.input_cost_per_million == 2.0
    assert pricing.output_cost_per_million == 8.0


def test_estimate_cost():
    pricing = TokenPricing(
        input_cost_per_million=2.0,
        output_cost_per_million=8.0,
    )

    result = estimate_cost(
        input_tokens=1000,
        output_tokens=500,
        pricing=pricing,
    )

    expected = (1000 * 2.0 / 1_000_000) + (
        500 * 8.0 / 1_000_000
    )

    assert result == pytest.approx(expected)