import logging
import time

from app.core.llm_provider_config import (
    LLMProviderSettings,
    llm_provider_settings,
)

from app.schemas.llm_provider import (
    LLMGenerationResult,
    LLMProviderAttempt,
    LLMProviderStatus,
)

from app.services.llm_providers.exceptions import (
    LLMProviderConfigurationError,
    LLMProviderUnavailableError,
    LLMProviderAuthenticationError,
    LLMProviderExecutionError,
    LLMAllProvidersFailedError,
)

from app.services.llm_providers.provider_registry import (
    LLMProviderRegistry,
    llm_provider_registry,
)


logger = logging.getLogger(__name__)


class LLMProviderRouter:

    def __init__(
        self,
        registry: LLMProviderRegistry = llm_provider_registry,
        settings: LLMProviderSettings = llm_provider_settings,
    ):

        self.registry = registry
        self.settings = settings

    def _provider_order(self) -> tuple[str, ...]:

        return (
            self.settings.primary_provider,
            *self.settings.fallback_providers,
        )

    async def generate(
        self,
        prompt: str,
    ) -> LLMGenerationResult:

        if not isinstance(prompt, str) or not prompt.strip():

            raise ValueError(
                "Prompt cannot be empty."
            )

        provider_order = self._provider_order()

        # Resolve all providers before execution.
        # A misspelled or unregistered fallback must not
        # silently produce partial provider configuration.

        providers = [
            self.registry.get(name)
            for name in provider_order
        ]

        attempts = []

        started_at = time.perf_counter()

        for index, provider in enumerate(providers):

            provider_started = time.perf_counter()

            try:

                response = await provider.generate(
                    prompt.strip()
                )

                if (
                    not isinstance(response, str)
                    or not response.strip()
                ):

                    raise LLMProviderExecutionError(
                        "Provider returned an empty response."
                    )

                provider_elapsed = (
                    time.perf_counter()
                    - provider_started
                ) * 1000

                attempts.append(
                    LLMProviderAttempt(
                        provider=provider.name,
                        success=True,
                        retryable=False,
                        execution_time_ms=round(
                            provider_elapsed,
                            3,
                        ),
                    )
                )

                total_elapsed = (
                    time.perf_counter()
                    - started_at
                ) * 1000

                status = (
                    LLMProviderStatus.SUCCESS
                    if index == 0
                    else LLMProviderStatus.FALLBACK_SUCCESS
                )

                logger.info(
                    "LLM generation succeeded: "
                    "provider=%s fallback=%s",
                    provider.name,
                    index > 0,
                )

                return LLMGenerationResult(
                    response=response.strip(),
                    provider=provider.name,
                    status=status,
                    attempts=attempts,
                    total_execution_time_ms=round(
                        total_elapsed,
                        3,
                    ),
                )

            except LLMProviderConfigurationError:

                # Configuration problems cannot be repaired
                # by switching providers automatically.
                raise

            except LLMProviderAuthenticationError:

                # Authentication failures are non-retryable.
                raise

            except LLMProviderUnavailableError as exc:

                retryable = True

                error_code = "provider_unavailable"

                logger.warning(
                    "LLM provider unavailable: provider=%s",
                    provider.name,
                )

            except LLMProviderExecutionError:

                retryable = False

                error_code = "provider_execution_failed"

                logger.exception(
                    "LLM provider execution failed: provider=%s",
                    provider.name,
                )

            except Exception:

                retryable = False

                error_code = "unexpected_provider_failure"

                logger.exception(
                    "Unexpected LLM provider failure: provider=%s",
                    provider.name,
                )

            provider_elapsed = (
                time.perf_counter()
                - provider_started
            ) * 1000

            attempts.append(
                LLMProviderAttempt(
                    provider=provider.name,
                    success=False,
                    retryable=retryable,
                    execution_time_ms=round(
                        provider_elapsed,
                        3,
                    ),
                    error_code=error_code,
                )
            )

            if not retryable:

                break

        total_elapsed = (
            time.perf_counter()
            - started_at
        ) * 1000

        logger.error(
            "All eligible LLM provider attempts failed."
        )

        raise LLMAllProvidersFailedError(
            "ScholarAI could not generate a response "
            "using the configured LLM providers.",
            attempts=attempts,
        )


llm_provider_router = LLMProviderRouter()