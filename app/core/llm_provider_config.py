import os

from dataclasses import dataclass


def _read_provider_name(
    name: str,
    default: str,
) -> str:

    value = os.getenv(name, default).strip().lower()

    if not value:
        raise ValueError(
            f"{name} cannot be empty."
        )

    return value


def _read_fallback_providers() -> tuple[str, ...]:

    raw_value = os.getenv(
        "SCHOLARAI_LLM_FALLBACK_PROVIDERS",
        "",
    )

    providers = tuple(
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    )

    if len(providers) != len(set(providers)):
        raise ValueError(
            "Fallback provider names must be unique."
        )

    return providers


@dataclass(frozen=True)
class LLMProviderSettings:

    primary_provider: str

    fallback_providers: tuple[str, ...]

    def __post_init__(self):

        configured = (
            self.primary_provider,
            *self.fallback_providers,
        )

        if len(configured) != len(set(configured)):

            raise ValueError(
                "Primary and fallback providers must be unique."
            )


def load_llm_provider_settings() -> LLMProviderSettings:

    return LLMProviderSettings(
        primary_provider=_read_provider_name(
            "SCHOLARAI_LLM_PRIMARY_PROVIDER",
            "gemini",
        ),
        fallback_providers=_read_fallback_providers(),
    )


llm_provider_settings = load_llm_provider_settings()