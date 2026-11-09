import logging

from app.services.llm_providers.base import (
    BaseLLMProvider,
)

from app.services.llm_providers.exceptions import (
    LLMProviderAuthenticationError,
    LLMProviderConfigurationError,
    LLMProviderExecutionError,
    LLMProviderUnavailableError,
)

from app.services.llm_service import (
    generate_llm_response,
)


logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):

    name = "gemini"

    def __init__(
        self,
        generator=None,
    ):

        self.generator = (
            generator or generate_llm_response
        )

    async def generate(
        self,
        prompt: str,
    ) -> str:

        if not isinstance(prompt, str) or not prompt.strip():

            raise ValueError(
                "Prompt cannot be empty."
            )

        try:

            response = await self.generator(
                prompt.strip()
            )

        except RuntimeError as exc:

            message = str(exc).lower()

            if "missing" in message and "api_key" in message:

                raise LLMProviderConfigurationError(
                    "Gemini API configuration is missing."
                ) from exc

            if (
                "authentication failed" in message
                or "access was denied" in message
            ):

                raise LLMProviderAuthenticationError(
                    "Gemini authentication failed."
                ) from exc

            if (
                "temporarily unavailable" in message
                or "usage limit reached" in message
            ):

                raise LLMProviderUnavailableError(
                    "Gemini is temporarily unavailable."
                ) from exc

            raise LLMProviderExecutionError(
                "Gemini response generation failed."
            ) from exc

        except (
            TimeoutError,
            ConnectionError,
        ) as exc:

            raise LLMProviderUnavailableError(
                "Gemini connection or request timed out."
            ) from exc

        except Exception as exc:

            logger.exception(
                "Unexpected Gemini adapter failure."
            )

            raise LLMProviderExecutionError(
                "Gemini execution failed."
            ) from exc

        if not isinstance(response, str) or not response.strip():

            raise LLMProviderExecutionError(
                "Gemini returned an invalid response."
            )

        return response.strip()