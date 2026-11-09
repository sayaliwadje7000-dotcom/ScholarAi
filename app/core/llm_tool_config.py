import os
from dataclasses import dataclass


def _positive_integer(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be a valid integer."
        ) from exc

    if value <= 0:
        raise ValueError(
            f"{name} must be greater than zero."
        )

    return value


@dataclass(frozen=True)
class LLMToolSettings:
    max_tool_calls_per_request: int
    tool_execution_timeout_seconds: int
    max_tool_arguments_bytes: int
    max_tool_output_characters: int


def load_llm_tool_settings() -> LLMToolSettings:
    return LLMToolSettings(
        max_tool_calls_per_request=_positive_integer(
            "SCHOLARAI_MAX_TOOL_CALLS",
            5,
        ),
        tool_execution_timeout_seconds=_positive_integer(
            "SCHOLARAI_TOOL_TIMEOUT_SECONDS",
            15,
        ),
        max_tool_arguments_bytes=_positive_integer(
            "SCHOLARAI_MAX_TOOL_ARGUMENTS_BYTES",
            16384,
        ),
        max_tool_output_characters=_positive_integer(
            "SCHOLARAI_MAX_TOOL_OUTPUT_CHARACTERS",
            12000,
        ),
    )


llm_tool_settings = load_llm_tool_settings()