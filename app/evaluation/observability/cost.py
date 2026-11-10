from collections.abc import Mapping

from app.evaluation.observability.schemas import ModelPricing


class CostEvaluationError(ValueError):
    pass


def estimate_model_cost(
    input_tokens: int,
    output_tokens: int,
    pricing: ModelPricing,
) -> float:
    if input_tokens < 0 or output_tokens < 0:
        raise CostEvaluationError("Token counts cannot be negative")

    input_cost = (
        input_tokens / 1000
    ) * pricing.input_cost_per_1k_tokens

    output_cost = (
        output_tokens / 1000
    ) * pricing.output_cost_per_1k_tokens

    return input_cost + output_cost


def estimate_cost_for_model(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    pricing_registry: Mapping[str, ModelPricing],
) -> float:
    pricing = pricing_registry.get(model_name)

    if pricing is None:
        raise CostEvaluationError(
            f"No pricing configuration found for model: {model_name}"
        )

    return estimate_model_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        pricing=pricing,
    )


def calculate_total_cost(costs: list[float]) -> float:
    if any(cost < 0 for cost in costs):
        raise CostEvaluationError("Costs cannot be negative")

    return sum(costs)


def calculate_average_cost(costs: list[float]) -> float:
    if not costs:
        return 0.0

    return calculate_total_cost(costs) / len(costs)
