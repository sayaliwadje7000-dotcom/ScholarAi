from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TokenPricing:
    input_cost_per_million: float
    output_cost_per_million: float

    def __post_init__(self):
        for value in (
            self.input_cost_per_million,
            self.output_cost_per_million,
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(
                    "Token pricing must be finite and non-negative."
                )


def estimate_cost(input_tokens, output_tokens, pricing):
    for value in (input_tokens, output_tokens):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                "Token counts must be non-negative integers."
            )

    input_cost = (
        input_tokens
        * pricing.input_cost_per_million
        / 1_000_000
    )

    output_cost = (
        output_tokens
        * pricing.output_cost_per_million
        / 1_000_000
    )

    return input_cost + output_cost